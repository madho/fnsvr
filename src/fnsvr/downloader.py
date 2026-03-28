"""Attachment downloading with MIME traversal for fnsvr."""
from __future__ import annotations

import base64
import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Replace unsafe characters with underscores.

    Any character that is not alphanumeric, dot, underscore, or hyphen
    is replaced with an underscore. Returns 'unnamed_attachment' for
    empty or fully-stripped results.
    """
    result = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    return result if result else "unnamed_attachment"


def unique_path(path: Path) -> Path:
    """Return a path that does not collide with existing files.

    If *path* does not exist, it is returned unchanged. Otherwise a
    counter suffix (_1, _2, ...) is appended before the extension until
    a free name is found. This guarantees no file is ever overwritten.
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def walk_parts(parts: list[dict] | None) -> list[dict]:
    """Flatten nested MIME part trees into a list of leaf parts.

    Recursively descends into parts that contain a nested ``parts``
    key (multipart containers) and collects all leaf nodes.
    """
    if not parts:
        return []
    leaves: list[dict] = []
    for part in parts:
        nested = part.get("parts")
        if nested:
            leaves.extend(walk_parts(nested))
        else:
            leaves.append(part)
    return leaves


def download_attachment(
    service,
    message_id: str,
    attachment_id: str,
    filename: str,
    save_dir: Path,
) -> tuple[str, int]:
    """Download a single attachment via the Gmail API.

    Args:
        service: Authenticated Gmail API service resource.
        message_id: Gmail message ID that owns the attachment.
        attachment_id: Gmail attachment ID.
        filename: Original filename (will be sanitized).
        save_dir: Directory to save the file into.

    Returns:
        Tuple of (local_path_string, size_in_bytes).
    """
    response = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    data = base64.urlsafe_b64decode(response["data"])
    safe_name = sanitize_filename(filename)
    save_path = unique_path(save_dir / safe_name)
    save_path.write_bytes(data)
    return (str(save_path), len(data))


def process_attachments(
    service,
    conn: sqlite3.Connection,
    email_row_id: int,
    message_id: str,
    parts: list[dict],
    save_dir: Path,
    allowed_extensions: list[str],
) -> int:
    """Process and download all eligible attachments for an email.

    Walks the MIME part tree, filters by *allowed_extensions*, downloads
    each attachment (either inline data or via the Gmail attachments API),
    and records the result in the ``attachments`` table.

    Failed downloads are logged and recorded with ``downloaded=0`` but
    do not raise to the caller.

    Args:
        service: Authenticated Gmail API service resource.
        conn: SQLite database connection.
        email_row_id: Row ID from ``detected_emails`` (foreign key).
        message_id: Gmail message ID.
        parts: Raw MIME parts list from the Gmail message payload.
        save_dir: Directory to save downloaded files into.
        allowed_extensions: List of lowercase extensions to accept (e.g. [".pdf"]).

    Returns:
        Number of successfully downloaded attachments.
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    download_count = 0

    for part in walk_parts(parts):
        filename = part.get("filename", "")
        if not filename:
            continue

        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            continue

        mime_type = part.get("mimeType", "")

        try:
            body = part.get("body", {})
            inline_data = body.get("data")
            attachment_id = body.get("attachmentId")

            if inline_data:
                # Small attachment -- data is embedded directly in the message
                data = base64.urlsafe_b64decode(inline_data)
                safe_name = sanitize_filename(filename)
                save_path = unique_path(save_dir / safe_name)
                save_path.write_bytes(data)
                local_path = str(save_path)
                size_bytes = len(data)
            elif attachment_id:
                # Large attachment -- must fetch separately via API
                local_path, size_bytes = download_attachment(
                    service, message_id, attachment_id, filename, save_dir
                )
            else:
                # No data source available for this part
                continue

            conn.execute(
                "INSERT INTO attachments "
                "(email_id, filename, local_path, mime_type, size_bytes, downloaded) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (email_row_id, filename, local_path, mime_type, size_bytes, 1),
            )
            conn.commit()
            download_count += 1

        except Exception as exc:
            logger.error(
                "Failed to download %s from message %s: %s", filename, message_id, exc
            )
            try:
                conn.execute(
                    "INSERT INTO attachments "
                    "(email_id, filename, local_path, mime_type, size_bytes, downloaded) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (email_row_id, filename, None, mime_type, None, 0),
                )
                conn.commit()
            except Exception as db_exc:
                logger.error("Failed to record attachment failure in DB: %s", db_exc)

    return download_count
