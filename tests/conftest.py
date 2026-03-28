"""Shared test fixtures for fnsvr."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_config() -> dict:
    """Return a valid config dict with all 4 required top-level keys."""
    return {
        "accounts": [
            {
                "name": "personal",
                "email": "test@gmail.com",
                "credentials_file": "credentials/personal_credentials.json",
                "token_file": "credentials/personal_token.json",
            }
        ],
        "paths": {
            "database": "~/test-fnsvr/data/fnsvr.db",
            "attachments": "~/test-fnsvr/data/attachments",
            "digests": "~/test-fnsvr/data/digests",
            "logs": "~/test-fnsvr/data/logs",
        },
        "categories": {
            "tax_documents": {
                "label": "Tax Documents",
                "priority": "critical",
                "subject_patterns": ["k-1", "1099", "w-2"],
                "sender_patterns": ["irs.gov", "turbotax"],
            }
        },
        "scan": {
            "initial_lookback_days": 90,
            "regular_lookback_days": 3,
            "max_results_per_scan": 100,
            "attachment_extensions": [".pdf", ".xlsx"],
        },
    }


@pytest.fixture
def db_conn(tmp_path):
    """Create a temporary SQLite database connection for testing."""
    from fnsvr.storage import init_db

    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def mock_gmail_service():
    """Return a mock Gmail API service object."""
    from unittest.mock import MagicMock

    service = MagicMock()
    return service


@pytest.fixture
def sample_message_payload():
    """Return a Gmail API message payload with headers and parts."""
    return {
        "id": "msg123",
        "snippet": "Your K-1 tax document is ready",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your K-1 Tax Document is Ready"},
                {"name": "From", "value": "tax@turbotax.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2026 10:00:00 -0500"},
            ],
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"size": 100},
                },
                {
                    "filename": "K1_2025.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att123", "size": 50000},
                },
            ],
        },
    }


@pytest.fixture
def sample_message_no_match():
    """Return a Gmail message that does NOT match any detection pattern."""
    return {
        "id": "msg456",
        "snippet": "Hey, want to grab lunch?",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Lunch plans for Friday"},
                {"name": "From", "value": "friend@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2026 12:00:00 -0500"},
            ],
            "mimeType": "text/plain",
            "parts": [],
        },
    }
