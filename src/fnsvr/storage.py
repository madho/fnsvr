"""SQLite database layer for fnsvr."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize database with schema. Returns configured connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS detected_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_email TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            subject TEXT,
            sender TEXT,
            date_received TEXT,
            snippet TEXT,
            matched_pattern TEXT,
            has_attachments INTEGER DEFAULT 0,
            notified INTEGER DEFAULT 0,
            reviewed INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(message_id, account_email)
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            local_path TEXT,
            mime_type TEXT,
            size_bytes INTEGER,
            downloaded INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (email_id) REFERENCES detected_emails(id)
        );

        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            account_email TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            emails_scanned INTEGER DEFAULT 0,
            emails_detected INTEGER DEFAULT 0,
            attachments_downloaded INTEGER DEFAULT 0,
            errors TEXT,
            status TEXT DEFAULT 'running'
        );

        CREATE INDEX IF NOT EXISTS idx_emails_account ON detected_emails(account_email);
        CREATE INDEX IF NOT EXISTS idx_emails_category ON detected_emails(category);
        CREATE INDEX IF NOT EXISTS idx_emails_priority ON detected_emails(priority);
        CREATE INDEX IF NOT EXISTS idx_emails_reviewed ON detected_emails(reviewed);
        CREATE INDEX IF NOT EXISTS idx_emails_date ON detected_emails(date_received);
    """)
    conn.commit()
    return conn


def insert_email(conn: sqlite3.Connection, email: dict) -> int | None:
    """Insert detected email. Returns row ID or None if duplicate."""
    try:
        cursor = conn.execute(
            """INSERT INTO detected_emails
               (message_id, account_name, account_email, category, priority,
                subject, sender, date_received, snippet, matched_pattern,
                has_attachments)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email["message_id"],
                email["account_name"],
                email["account_email"],
                email["category"],
                email["priority"],
                email["subject"],
                email["sender"],
                email["date_received"],
                email.get("snippet", "")[:500],
                email["matched_pattern"],
                email.get("has_attachments", 0),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_unreviewed(
    conn: sqlite3.Connection,
    category: str | None = None,
    account: str | None = None,
) -> list[sqlite3.Row]:
    """Get unreviewed emails, optionally filtered by category or account."""
    query = "SELECT * FROM detected_emails WHERE reviewed = 0"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if account:
        query += " AND account_email = ?"
        params.append(account)
    query += " ORDER BY priority ASC, date_received DESC"
    return conn.execute(query, params).fetchall()


def mark_reviewed(
    conn: sqlite3.Connection, email_id: int, notes: str | None = None
) -> None:
    """Mark an email as reviewed with optional notes."""
    conn.execute(
        "UPDATE detected_emails SET reviewed = 1, notes = ? WHERE id = ?",
        (notes, email_id),
    )
    conn.commit()


def get_stats(conn: sqlite3.Connection) -> dict:
    """Get summary statistics from the database."""
    total = conn.execute("SELECT COUNT(*) FROM detected_emails").fetchone()[0]
    unreviewed = conn.execute(
        "SELECT COUNT(*) FROM detected_emails WHERE reviewed = 0"
    ).fetchone()[0]
    by_category: dict[str, int] = {}
    for row in conn.execute(
        "SELECT category, COUNT(*) as cnt FROM detected_emails GROUP BY category"
    ).fetchall():
        by_category[row["category"]] = row["cnt"]
    by_priority: dict[str, int] = {}
    for row in conn.execute(
        "SELECT priority, COUNT(*) as cnt FROM detected_emails GROUP BY priority"
    ).fetchall():
        by_priority[row["priority"]] = row["cnt"]
    return {
        "total": total,
        "unreviewed": unreviewed,
        "by_category": by_category,
        "by_priority": by_priority,
    }


def insert_scan_log(
    conn: sqlite3.Connection, account_name: str, account_email: str, started_at: str
) -> int:
    """Create a new scan log entry. Returns row ID."""
    cursor = conn.execute(
        """INSERT INTO scan_log (account_name, account_email, started_at)
           VALUES (?, ?, ?)""",
        (account_name, account_email, started_at),
    )
    conn.commit()
    return cursor.lastrowid


def update_scan_log(
    conn: sqlite3.Connection,
    log_id: int,
    *,
    completed_at: str,
    emails_scanned: int,
    emails_detected: int,
    attachments_downloaded: int = 0,
    errors: str | None = None,
    status: str = "completed",
) -> None:
    """Update a scan log entry with results."""
    conn.execute(
        """UPDATE scan_log SET completed_at = ?, emails_scanned = ?,
           emails_detected = ?, attachments_downloaded = ?, errors = ?,
           status = ? WHERE id = ?""",
        (
            completed_at,
            emails_scanned,
            emails_detected,
            attachments_downloaded,
            errors,
            status,
            log_id,
        ),
    )
    conn.commit()
