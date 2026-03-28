"""Tests for fnsvr.scanner -- Gmail API integration with mocked Google APIs."""
from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from fnsvr import scanner
from fnsvr.detector import CompiledCategory


# ---------------------------------------------------------------------------
# AUTH-02: SCOPES readonly
# ---------------------------------------------------------------------------

def test_scopes_readonly():
    """SCOPES must contain only gmail.readonly."""
    assert scanner.SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert len(scanner.SCOPES) == 1


# ---------------------------------------------------------------------------
# AUTH-01, AUTH-03: setup_oauth
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.InstalledAppFlow.from_client_secrets_file")
def test_setup_oauth(mock_flow_cls, tmp_path):
    """setup_oauth stores a token file with 0o600 permissions."""
    # Create a fake credentials file
    creds_dir = tmp_path / "credentials"
    creds_dir.mkdir()
    creds_file = creds_dir / "personal_credentials.json"
    creds_file.write_text('{"installed": {}}')

    # Mock the flow
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "test"}'
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    mock_flow_cls.return_value = mock_flow

    account = {
        "name": "personal",
        "credentials_file": "credentials/personal_credentials.json",
        "token_file": "credentials/personal_token.json",
    }

    result = scanner.setup_oauth(account, tmp_path)

    assert result is True
    token_path = tmp_path / "credentials" / "personal_token.json"
    assert token_path.exists()
    assert token_path.read_text() == '{"token": "test"}'
    # Verify 600 permissions
    mode = os.stat(token_path).st_mode & 0o777
    assert mode == 0o600


def test_setup_oauth_missing_credentials(tmp_path):
    """setup_oauth raises FileNotFoundError for missing credentials file."""
    account = {
        "name": "personal",
        "credentials_file": "credentials/nonexistent.json",
        "token_file": "credentials/personal_token.json",
    }
    with pytest.raises(FileNotFoundError, match="Credentials file not found"):
        scanner.setup_oauth(account, tmp_path)


# ---------------------------------------------------------------------------
# AUTH-03: Token permissions
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.InstalledAppFlow.from_client_secrets_file")
def test_token_permissions(mock_flow_cls, tmp_path):
    """Token file must have exactly 0o600 permissions after setup."""
    creds_dir = tmp_path / "credentials"
    creds_dir.mkdir()
    (creds_dir / "creds.json").write_text('{"installed": {}}')

    mock_creds = MagicMock()
    mock_creds.to_json.return_value = "{}"
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    mock_flow_cls.return_value = mock_flow

    account = {
        "name": "test",
        "credentials_file": "credentials/creds.json",
        "token_file": "credentials/token.json",
    }
    scanner.setup_oauth(account, tmp_path)

    token_path = tmp_path / "credentials" / "token.json"
    mode = os.stat(token_path).st_mode & 0o777
    assert mode == 0o600


# ---------------------------------------------------------------------------
# AUTH-04: Token refresh
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.build")
@patch("fnsvr.scanner.Request")
@patch("fnsvr.scanner.Credentials.from_authorized_user_file")
def test_token_refresh(mock_from_file, mock_request_cls, mock_build, tmp_path):
    """get_gmail_service refreshes expired tokens and returns a service."""
    # Create token file
    token_dir = tmp_path / "credentials"
    token_dir.mkdir()
    token_path = token_dir / "token.json"
    token_path.write_text("{}")
    os.chmod(str(token_path), 0o600)

    # Mock credentials: expired but has refresh token
    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_tok"
    mock_creds.valid = True
    mock_creds.to_json.return_value = '{"refreshed": true}'
    mock_from_file.return_value = mock_creds

    mock_service = MagicMock()
    mock_build.return_value = mock_service

    account = {
        "name": "personal",
        "token_file": "credentials/token.json",
    }
    result = scanner.get_gmail_service(account, tmp_path)

    mock_creds.refresh.assert_called_once()
    assert result is mock_service


# ---------------------------------------------------------------------------
# AUTH-05: Refresh failure returns None
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.Credentials.from_authorized_user_file")
def test_refresh_failure_message(mock_from_file, tmp_path):
    """get_gmail_service returns None (not raises) on RefreshError."""
    from google.auth.exceptions import RefreshError

    token_dir = tmp_path / "credentials"
    token_dir.mkdir()
    token_path = token_dir / "token.json"
    token_path.write_text("{}")

    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.refresh_token = "tok"
    mock_creds.refresh.side_effect = RefreshError("refresh failed")
    mock_from_file.return_value = mock_creds

    account = {
        "name": "personal",
        "token_file": "credentials/token.json",
    }
    result = scanner.get_gmail_service(account, tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# get_header
# ---------------------------------------------------------------------------

def test_get_header():
    """get_header extracts values case-insensitively."""
    headers = [
        {"name": "Subject", "value": "Hello World"},
        {"name": "From", "value": "test@example.com"},
    ]
    assert scanner.get_header(headers, "Subject") == "Hello World"
    assert scanner.get_header(headers, "subject") == "Hello World"
    assert scanner.get_header(headers, "SUBJECT") == "Hello World"
    assert scanner.get_header(headers, "From") == "test@example.com"
    assert scanner.get_header(headers, "X-Missing") == ""


# ---------------------------------------------------------------------------
# SCAN-01, SCAN-02, SCAN-03: build_query
# ---------------------------------------------------------------------------

def test_build_query():
    """build_query(3) returns epoch-based query for 3-day lookback."""
    result = scanner.build_query(3)
    assert result.startswith("after:")
    epoch = int(result.split(":")[1])
    expected = int(time.time()) - (3 * 86400)
    assert abs(epoch - expected) <= 5


def test_initial_lookback():
    """build_query(90) returns epoch for 90-day lookback (SCAN-02)."""
    result = scanner.build_query(90)
    epoch = int(result.split(":")[1])
    expected = int(time.time()) - (90 * 86400)
    assert abs(epoch - expected) <= 5


def test_custom_lookback():
    """build_query(14) returns epoch for 14-day lookback (SCAN-03)."""
    result = scanner.build_query(14)
    epoch = int(result.split(":")[1])
    expected = int(time.time()) - (14 * 86400)
    assert abs(epoch - expected) <= 5


# ---------------------------------------------------------------------------
# SCAN-01: scan_all default flow
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.get_gmail_service")
def test_scan_all_default(
    mock_get_service, sample_config, db_conn, sample_message_payload, tmp_path
):
    """scan_all scans all accounts and creates scan_log entries (SCAN-01)."""
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    # messages().list returns one message
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg123"}]
    }
    # messages().get returns sample payload
    mock_service.users().messages().get().execute.return_value = sample_message_payload

    results = scanner.scan_all(sample_config, db_conn, 3, tmp_path)

    assert len(results) == 1
    name, scanned, detected, downloaded, error = results[0]
    assert name == "personal"
    assert scanned == 1
    assert error is None

    # Verify scan_log entry
    row = db_conn.execute("SELECT * FROM scan_log WHERE account_name = 'personal'").fetchone()
    assert row is not None
    assert row["status"] in ("completed", "completed_with_errors")


# ---------------------------------------------------------------------------
# SCAN-04: Single account filter
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.get_gmail_service")
def test_single_account(mock_get_service, sample_config, db_conn, tmp_path):
    """scan_all with account_filter scans only that account (SCAN-04)."""
    # Add a second account to config
    sample_config["accounts"].append({
        "name": "work",
        "email": "work@gmail.com",
        "credentials_file": "credentials/work_credentials.json",
        "token_file": "credentials/work_token.json",
    })

    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.users().messages().list().execute.return_value = {"messages": []}

    results = scanner.scan_all(sample_config, db_conn, 3, tmp_path, account_filter="personal")

    assert len(results) == 1
    assert results[0][0] == "personal"
    # get_gmail_service called only once (for the filtered account)
    assert mock_get_service.call_count == 1


# ---------------------------------------------------------------------------
# SCAN-05: Error isolation
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.get_gmail_service")
def test_error_isolation(mock_get_service, sample_config, db_conn, tmp_path):
    """One account failure does not block scanning of other accounts (SCAN-05)."""
    sample_config["accounts"].append({
        "name": "work",
        "email": "work@gmail.com",
        "credentials_file": "credentials/work_credentials.json",
        "token_file": "credentials/work_token.json",
    })

    # First account fails auth, second succeeds
    def side_effect(account, config_dir):
        if account["name"] == "personal":
            return None  # will cause RuntimeError in scan_account
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {"messages": []}
        return mock_service

    mock_get_service.side_effect = side_effect

    results = scanner.scan_all(sample_config, db_conn, 3, tmp_path)

    assert len(results) == 2
    # First account has error
    assert results[0][0] == "personal"
    assert results[0][4] is not None  # error string present
    # Second account succeeded
    assert results[1][0] == "work"
    assert results[1][4] is None  # no error


# ---------------------------------------------------------------------------
# SCAN-06: Scan logging
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.get_gmail_service")
def test_scan_logging(
    mock_get_service, sample_config, db_conn, sample_message_payload, tmp_path
):
    """scan_account creates scan_log with correct fields (SCAN-06)."""
    from fnsvr.detector import compile_patterns

    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg123"}]
    }
    mock_service.users().messages().get().execute.return_value = sample_message_payload

    patterns = compile_patterns(sample_config["categories"])
    account = sample_config["accounts"][0]

    scanned, detected, downloaded = scanner.scan_account(
        account, sample_config, db_conn, patterns, 3, tmp_path
    )

    assert scanned == 1
    assert detected == 1  # "K-1 Tax Document" matches tax_documents pattern
    assert downloaded == 0

    # Verify scan_log
    row = db_conn.execute("SELECT * FROM scan_log WHERE account_name = 'personal'").fetchone()
    assert row is not None
    assert row["started_at"] is not None
    assert row["completed_at"] is not None
    assert row["emails_scanned"] == 1
    assert row["emails_detected"] == 1
    assert row["status"] == "completed"


# ---------------------------------------------------------------------------
# fetch_message_ids pagination
# ---------------------------------------------------------------------------

@patch("fnsvr.scanner.get_gmail_service")
def test_fetch_message_ids_empty(mock_get_service):
    """fetch_message_ids returns empty list when no messages match."""
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.return_value = {}
    result = scanner.fetch_message_ids(mock_service, "after:0", 100)
    assert result == []
