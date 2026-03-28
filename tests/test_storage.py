"""Unit tests for fnsvr.storage module."""
from __future__ import annotations

import sqlite3

import pytest


def _sample_email(**overrides) -> dict:
    base = {
        "message_id": "msg_001",
        "account_name": "personal",
        "account_email": "test@gmail.com",
        "category": "tax_documents",
        "priority": "critical",
        "subject": "Your K-1 is ready",
        "sender": "noreply@schwab.com",
        "date_received": "2026-03-15T10:00:00Z",
        "snippet": "Your Schedule K-1 tax document is now available.",
        "matched_pattern": "subject:k-1",
        "has_attachments": 1,
    }
    base.update(overrides)
    return base


class TestInitDb:
    def test_init_db_creates_tables(self, db_conn):
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = sorted(row["name"] for row in rows)
        assert "attachments" in table_names
        assert "detected_emails" in table_names
        assert "scan_log" in table_names

    def test_wal_mode(self, db_conn):
        mode = db_conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_foreign_keys_on(self, db_conn):
        fk = db_conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

    def test_indexes(self, db_conn):
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        index_names = {row["name"] for row in rows}
        expected = {
            "idx_emails_account",
            "idx_emails_category",
            "idx_emails_priority",
            "idx_emails_reviewed",
            "idx_emails_date",
        }
        assert expected.issubset(index_names)

    def test_row_factory(self, db_conn):
        assert db_conn.row_factory is sqlite3.Row


class TestInsertEmail:
    def test_insert_email(self, db_conn):
        from fnsvr.storage import insert_email

        row_id = insert_email(db_conn, _sample_email())
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_dedup_insert(self, db_conn):
        from fnsvr.storage import insert_email

        first = insert_email(db_conn, _sample_email())
        second = insert_email(db_conn, _sample_email())
        assert isinstance(first, int)
        assert second is None

    def test_snippet_truncation(self, db_conn):
        from fnsvr.storage import insert_email

        long_snippet = "A" * 600
        insert_email(db_conn, _sample_email(snippet=long_snippet))
        row = db_conn.execute(
            "SELECT snippet FROM detected_emails WHERE message_id = 'msg_001'"
        ).fetchone()
        assert len(row["snippet"]) <= 500


class TestQueries:
    def test_get_unreviewed(self, db_conn):
        from fnsvr.storage import insert_email, get_unreviewed

        insert_email(db_conn, _sample_email(message_id="unrev_1", reviewed=0))
        # Insert a reviewed one manually
        insert_email(db_conn, _sample_email(message_id="rev_1"))
        db_conn.execute(
            "UPDATE detected_emails SET reviewed = 1 WHERE message_id = 'rev_1'"
        )
        db_conn.commit()

        results = get_unreviewed(db_conn)
        assert len(results) == 1
        assert results[0]["message_id"] == "unrev_1"

    def test_mark_reviewed(self, db_conn):
        from fnsvr.storage import insert_email, mark_reviewed

        row_id = insert_email(db_conn, _sample_email())
        mark_reviewed(db_conn, row_id, notes="Looks good")
        row = db_conn.execute(
            "SELECT reviewed, notes FROM detected_emails WHERE id = ?", (row_id,)
        ).fetchone()
        assert row["reviewed"] == 1
        assert row["notes"] == "Looks good"

    def test_get_stats(self, db_conn):
        from fnsvr.storage import insert_email, get_stats

        insert_email(db_conn, _sample_email(message_id="s1", category="tax_documents"))
        insert_email(db_conn, _sample_email(message_id="s2", category="tax_documents"))
        insert_email(
            db_conn,
            _sample_email(message_id="s3", category="equity_grants"),
        )

        stats = get_stats(db_conn)
        assert stats["total"] == 3
        assert stats["by_category"]["tax_documents"] == 2
        assert stats["by_category"]["equity_grants"] == 1


class TestScanLog:
    def test_insert_scan_log(self, db_conn):
        from fnsvr.storage import insert_scan_log

        log_id = insert_scan_log(db_conn, "personal", "test@gmail.com", "2026-03-15T10:00:00Z")
        assert isinstance(log_id, int)
        assert log_id > 0

        row = db_conn.execute("SELECT * FROM scan_log WHERE id = ?", (log_id,)).fetchone()
        assert row["status"] == "running"

    def test_update_scan_log(self, db_conn):
        from fnsvr.storage import insert_scan_log, update_scan_log

        log_id = insert_scan_log(db_conn, "personal", "test@gmail.com", "2026-03-15T10:00:00Z")
        update_scan_log(
            db_conn,
            log_id,
            completed_at="2026-03-15T10:05:00Z",
            emails_scanned=50,
            emails_detected=3,
            attachments_downloaded=2,
            status="completed",
        )

        row = db_conn.execute("SELECT * FROM scan_log WHERE id = ?", (log_id,)).fetchone()
        assert row["completed_at"] == "2026-03-15T10:05:00Z"
        assert row["emails_scanned"] == 50
        assert row["emails_detected"] == 3
        assert row["attachments_downloaded"] == 2
        assert row["status"] == "completed"
