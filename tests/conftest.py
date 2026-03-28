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
