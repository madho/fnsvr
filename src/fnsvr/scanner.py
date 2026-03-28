"""Gmail API integration: OAuth authentication and multi-account email scanning.

This module connects fnsvr to Gmail via the google-api-python-client library.
It handles OAuth token management (browser-based flow, auto-refresh) and
orchestrates scanning across multiple accounts, coordinating with the detector
and storage modules.

Scope: gmail.readonly only. fnsvr never modifies, deletes, or sends email.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from fnsvr import config as config_module, detector, downloader, notifier, storage
from fnsvr.detector import CompiledCategory

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def setup_oauth(account: dict, config_dir: Path) -> bool:
    """Run interactive OAuth flow for a Gmail account.

    Opens the default browser for Google consent. On success, stores the
    resulting token JSON file with 600 permissions.

    Args:
        account: Account dict with ``credentials_file`` and ``token_file`` keys.
        config_dir: Base directory for resolving relative credential paths.

    Returns:
        True on success.

    Raises:
        FileNotFoundError: If the OAuth client credentials file does not exist.
    """
    creds_path = config_dir / account["credentials_file"]
    token_path = config_dir / account["token_file"]

    if not creds_path.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {creds_path}\n"
            "Download OAuth client credentials from Google Cloud Console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    os.chmod(str(token_path), 0o600)

    logger.info("OAuth token stored for %s at %s", account["name"], token_path)
    return True


def get_gmail_service(account: dict, config_dir: Path):
    """Build an authenticated Gmail API service for the given account.

    Loads the stored OAuth token, auto-refreshes if expired, and returns
    a Gmail API service object. Returns None if authentication fails.

    Args:
        account: Account dict with ``token_file`` key.
        config_dir: Base directory for resolving relative credential paths.

    Returns:
        A Gmail API service resource, or None if auth fails.
    """
    token_path = config_dir / account["token_file"]

    if not token_path.exists():
        logger.warning("No token file for %s at %s", account["name"], token_path)
        return None

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            os.chmod(str(token_path), 0o600)
            logger.info("Token refreshed for %s", account["name"])
        except RefreshError:
            logger.error(
                "Token refresh failed for %s. Re-run: fnsvr setup %s",
                account["name"],
                account["name"],
            )
            return None

    if not creds or not creds.valid:
        logger.error("Invalid credentials for %s", account["name"])
        return None

    return build("gmail", "v1", credentials=creds)


def get_header(headers: list[dict], name: str) -> str:
    """Extract a header value from a Gmail message header list.

    Args:
        headers: List of ``{"name": ..., "value": ...}`` dicts from Gmail API.
        name: Header name to find (case-insensitive).

    Returns:
        The header value, or empty string if not found.
    """
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value", "")
    return ""


def build_query(lookback_days: int) -> str:
    """Build a Gmail search query for messages within a date range.

    Uses epoch timestamps to avoid timezone ambiguity.

    Args:
        lookback_days: Number of days to look back from now.

    Returns:
        Gmail search query string, e.g. ``"after:1700000000"``.
    """
    epoch = int(time.time()) - (lookback_days * 86400)
    return f"after:{epoch}"


def fetch_message_ids(service, query: str, max_results: int) -> list[str]:
    """Fetch message IDs matching a Gmail search query.

    Handles pagination via nextPageToken and enforces a hard cap.

    Args:
        service: Authenticated Gmail API service.
        query: Gmail search query string.
        max_results: Maximum number of message IDs to return.

    Returns:
        List of Gmail message ID strings.
    """
    ids: list[str] = []
    page_token = None
    remaining = max_results

    while remaining > 0:
        page_size = min(remaining, 500)
        request_kwargs: dict = {
            "userId": "me",
            "q": query,
            "maxResults": page_size,
        }
        if page_token:
            request_kwargs["pageToken"] = page_token

        response = service.users().messages().list(**request_kwargs).execute()
        messages = response.get("messages", [])
        if not messages:
            break

        for msg in messages:
            if remaining <= 0:
                break
            ids.append(msg["id"])
            remaining -= 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return ids


def _has_attachments(payload: dict) -> bool:
    """Check if a message payload contains attachments (recursive)."""
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("filename"):
            return True
        if _has_attachments(part):
            return True
    return False


def scan_account(
    account: dict,
    config: dict,
    conn: sqlite3.Connection,
    patterns: list[CompiledCategory],
    lookback_days: int,
    config_dir: Path,
) -> tuple[int, int, int]:
    """Scan a single Gmail account for financial emails.

    Fetches messages within the lookback window, runs detection, and stores
    matches. Logs the scan start and completion to the scan_log table.

    Args:
        account: Account dict with name, email, token_file keys.
        config: Full config dict (needs scan.max_results_per_scan).
        conn: SQLite database connection.
        patterns: Compiled detection patterns from detector.compile_patterns.
        lookback_days: Number of days to look back.
        config_dir: Base directory for resolving credential paths.

    Returns:
        Tuple of (emails_scanned, emails_detected, attachments_downloaded).
        Attachments downloaded is always 0 (handled by downloader module).

    Raises:
        RuntimeError: If Gmail authentication fails for this account.
    """
    service = get_gmail_service(account, config_dir)
    if service is None:
        raise RuntimeError(
            f"Authentication failed for {account['name']}. "
            f"Run: fnsvr setup {account['name']}"
        )

    started_at = datetime.now(timezone.utc).isoformat()
    log_id = storage.insert_scan_log(conn, account["name"], account["email"], started_at)

    query = build_query(lookback_days)
    max_results = config["scan"]["max_results_per_scan"]
    message_ids = fetch_message_ids(service, query, max_results)

    scanned = 0
    detected = 0
    downloaded_total = 0
    errors: list[str] = []
    new_detections: list[dict] = []

    # Resolve attachment save directory and allowed extensions
    attachments_base = config_module.resolve_path(config["paths"]["attachments"])
    save_dir = attachments_base / account["name"]
    allowed_ext = config["scan"].get(
        "attachment_extensions", [".pdf", ".xlsx", ".xls", ".csv", ".doc", ".docx"]
    )

    for msg_id in message_ids:
        try:
            message = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            subject = get_header(headers, "Subject")
            sender = get_header(headers, "From")
            date_received = get_header(headers, "Date")
            snippet = message.get("snippet", "")
            has_attach = _has_attachments(payload)

            scanned += 1

            match = detector.match_email(subject, sender, patterns)
            if match:
                email_row_id = storage.insert_email(conn, {
                    "message_id": msg_id,
                    "account_name": account["name"],
                    "account_email": account["email"],
                    "category": match.category,
                    "priority": match.priority,
                    "subject": subject,
                    "sender": sender,
                    "date_received": date_received,
                    "snippet": snippet,
                    "matched_pattern": match.matched_pattern,
                    "has_attachments": 1 if has_attach else 0,
                })
                detected += 1

                # Track genuinely new detections for notifications
                if email_row_id is not None:
                    new_detections.append({
                        "category": match.category,
                        "priority": match.priority,
                        "subject": subject,
                        "account_name": account["name"],
                    })

                # Download attachments for matched emails
                if email_row_id is not None:
                    parts = payload.get("parts", [])
                    if parts:
                        try:
                            dl_count = downloader.process_attachments(
                                service, conn, email_row_id, msg_id,
                                parts, save_dir, allowed_ext,
                            )
                            downloaded_total += dl_count
                        except Exception as exc:
                            logger.error(
                                "Attachment processing failed for %s: %s", msg_id, exc
                            )
        except Exception as exc:
            error_msg = f"Error processing message {msg_id}: {exc}"
            logger.warning(error_msg)
            errors.append(error_msg)

    # Send notifications for new detections (never blocks scanning)
    if new_detections:
        try:
            notifier.notify_detections(new_detections, config)
        except Exception as exc:
            logger.warning("Notification failed: %s", exc)

    status = "completed"
    if errors:
        status = "completed_with_errors"

    completed_at = datetime.now(timezone.utc).isoformat()
    storage.update_scan_log(
        conn,
        log_id,
        completed_at=completed_at,
        emails_scanned=scanned,
        emails_detected=detected,
        attachments_downloaded=downloaded_total,
        errors="\n".join(errors) if errors else None,
        status=status,
    )

    logger.info(
        "Scan complete for %s: %d scanned, %d detected, %d downloaded, %d errors",
        account["name"],
        scanned,
        detected,
        downloaded_total,
        len(errors),
    )
    return (scanned, detected, downloaded_total)


def scan_all(
    config: dict,
    conn: sqlite3.Connection,
    lookback_days: int,
    config_dir: Path,
    account_filter: str | None = None,
) -> list[tuple]:
    """Scan all configured Gmail accounts (or a single filtered account).

    Compiles detection patterns once, then iterates accounts. Each account
    is wrapped in try/except so one failure does not block others.

    Args:
        config: Full config dict with accounts, categories, scan keys.
        conn: SQLite database connection.
        lookback_days: Number of days to look back.
        config_dir: Base directory for resolving credential paths.
        account_filter: If provided, only scan the account with this name.

    Returns:
        List of tuples: (account_name, scanned, detected, downloaded, error).
        Error is None on success, or a string describing the failure.
    """
    patterns = detector.compile_patterns(config["categories"])
    accounts = config["accounts"]

    if account_filter is not None:
        accounts = [a for a in accounts if a["name"] == account_filter]

    results: list[tuple] = []
    for account in accounts:
        try:
            scanned, detected, downloaded = scan_account(
                account, config, conn, patterns, lookback_days, config_dir
            )
            results.append((account["name"], scanned, detected, downloaded, None))
        except Exception as exc:
            logger.error("Scan failed for %s: %s", account["name"], exc)
            results.append((account["name"], 0, 0, 0, str(exc)))

    return results
