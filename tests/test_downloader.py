"""Tests for fnsvr.downloader -- attachment download logic."""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fnsvr.downloader import (
    download_attachment,
    process_attachments,
    sanitize_filename,
    unique_path,
    walk_parts,
)


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_parentheses_and_spaces(self) -> None:
        assert sanitize_filename("K1 (2025).pdf") == "K1__2025_.pdf"

    def test_already_safe(self) -> None:
        assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"

    def test_spaces_replaced(self) -> None:
        assert sanitize_filename("file with spaces.xlsx") == "file_with_spaces.xlsx"

    def test_empty_string(self) -> None:
        assert sanitize_filename("") == "unnamed_attachment"


# ---------------------------------------------------------------------------
# unique_path
# ---------------------------------------------------------------------------


class TestUniquePath:
    def test_no_conflict(self, tmp_path: Path) -> None:
        result = unique_path(tmp_path / "test.pdf")
        assert result == tmp_path / "test.pdf"

    def test_with_conflict(self, tmp_path: Path) -> None:
        (tmp_path / "test.pdf").write_bytes(b"existing")
        result = unique_path(tmp_path / "test.pdf")
        assert result == tmp_path / "test_1.pdf"

    def test_multiple_conflicts(self, tmp_path: Path) -> None:
        (tmp_path / "test.pdf").write_bytes(b"existing")
        (tmp_path / "test_1.pdf").write_bytes(b"existing")
        result = unique_path(tmp_path / "test.pdf")
        assert result == tmp_path / "test_2.pdf"


# ---------------------------------------------------------------------------
# walk_parts
# ---------------------------------------------------------------------------


class TestWalkParts:
    def test_flat(self) -> None:
        parts = [
            {"mimeType": "application/pdf", "filename": "a.pdf"},
            {"mimeType": "text/csv", "filename": "b.csv"},
        ]
        result = walk_parts(parts)
        assert len(result) == 2
        assert result[0]["filename"] == "a.pdf"
        assert result[1]["filename"] == "b.csv"

    def test_nested(self) -> None:
        parts = [
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "application/pdf", "filename": "a.pdf"},
                    {"mimeType": "text/csv", "filename": "b.csv"},
                ],
            }
        ]
        result = walk_parts(parts)
        assert len(result) == 2
        assert result[0]["filename"] == "a.pdf"
        assert result[1]["filename"] == "b.csv"

    def test_none(self) -> None:
        assert walk_parts(None) == []

    def test_empty(self) -> None:
        assert walk_parts([]) == []


# ---------------------------------------------------------------------------
# Helpers for DB tests
# ---------------------------------------------------------------------------


def _insert_email(conn) -> int:
    """Insert a detected_email row and return its ID."""
    row_id = conn.execute(
        "INSERT INTO detected_emails "
        "(message_id, account_name, account_email, category, priority, subject, sender) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("msg1", "personal", "test@gmail.com", "tax_documents", "critical", "K-1", "irs@example.com"),
    ).lastrowid
    conn.commit()
    return row_id


def _make_part(filename: str, mime: str, *, inline_data: bytes | None = None, attachment_id: str | None = None) -> dict:
    """Build a Gmail-style MIME part dict."""
    body: dict = {}
    if inline_data is not None:
        body["data"] = base64.urlsafe_b64encode(inline_data).decode()
    if attachment_id is not None:
        body["attachmentId"] = attachment_id
    return {"filename": filename, "mimeType": mime, "body": body}


# ---------------------------------------------------------------------------
# process_attachments -- extension filter (ATT-02)
# ---------------------------------------------------------------------------


def test_extension_filter(db_conn, tmp_path: Path) -> None:
    email_id = _insert_email(db_conn)
    parts = [
        _make_part("report.pdf", "application/pdf", inline_data=b"pdf-content"),
        _make_part("photo.jpg", "image/jpeg", inline_data=b"jpg-content"),
    ]
    count = process_attachments(
        service=MagicMock(),
        conn=db_conn,
        email_row_id=email_id,
        message_id="msg1",
        parts=parts,
        save_dir=tmp_path / "personal",
        allowed_extensions=[".pdf"],
    )
    assert count == 1
    rows = db_conn.execute("SELECT * FROM attachments WHERE downloaded = 1").fetchall()
    assert len(rows) == 1
    assert rows[0]["filename"] == "report.pdf"


# ---------------------------------------------------------------------------
# download_attachment (ATT-01)
# ---------------------------------------------------------------------------


def test_download_detected(tmp_path: Path) -> None:
    raw_bytes = b"fake-pdf-content-here"
    encoded = base64.urlsafe_b64encode(raw_bytes).decode()

    mock_service = MagicMock()
    mock_service.users().messages().attachments().get().execute.return_value = {
        "data": encoded,
    }

    local_path, size = download_attachment(
        service=mock_service,
        message_id="msg1",
        attachment_id="att1",
        filename="statement.pdf",
        save_dir=tmp_path,
    )
    assert Path(local_path).exists()
    assert size == len(raw_bytes)
    assert Path(local_path).read_bytes() == raw_bytes


# ---------------------------------------------------------------------------
# save path / directory creation (ATT-03)
# ---------------------------------------------------------------------------


def test_save_path(db_conn, tmp_path: Path) -> None:
    email_id = _insert_email(db_conn)
    save_dir = tmp_path / "personal"
    parts = [
        _make_part("report.pdf", "application/pdf", inline_data=b"content"),
    ]
    process_attachments(
        service=MagicMock(),
        conn=db_conn,
        email_row_id=email_id,
        message_id="msg1",
        parts=parts,
        save_dir=save_dir,
        allowed_extensions=[".pdf"],
    )
    assert save_dir.exists()
    files = list(save_dir.iterdir())
    assert len(files) == 1


# ---------------------------------------------------------------------------
# no overwrite (ATT-04)
# ---------------------------------------------------------------------------


def test_no_overwrite(db_conn, tmp_path: Path) -> None:
    email_id = _insert_email(db_conn)
    save_dir = tmp_path / "personal"
    save_dir.mkdir(parents=True)
    (save_dir / "test.pdf").write_bytes(b"original")

    parts = [
        _make_part("test.pdf", "application/pdf", inline_data=b"new-content"),
    ]
    process_attachments(
        service=MagicMock(),
        conn=db_conn,
        email_row_id=email_id,
        message_id="msg1",
        parts=parts,
        save_dir=save_dir,
        allowed_extensions=[".pdf"],
    )
    # Original untouched
    assert (save_dir / "test.pdf").read_bytes() == b"original"
    # New file saved with counter suffix
    assert (save_dir / "test_1.pdf").exists()
    assert (save_dir / "test_1.pdf").read_bytes() == b"new-content"


# ---------------------------------------------------------------------------
# download failure resilience (ATT-05)
# ---------------------------------------------------------------------------


def test_download_failure(db_conn, tmp_path: Path) -> None:
    email_id = _insert_email(db_conn)

    mock_service = MagicMock()
    mock_service.users().messages().attachments().get().execute.side_effect = Exception(
        "API error"
    )

    parts = [
        _make_part("broken.pdf", "application/pdf", attachment_id="att_broken"),
    ]
    count = process_attachments(
        service=mock_service,
        conn=db_conn,
        email_row_id=email_id,
        message_id="msg1",
        parts=parts,
        save_dir=tmp_path / "personal",
        allowed_extensions=[".pdf"],
    )
    assert count == 0
    rows = db_conn.execute("SELECT * FROM attachments WHERE downloaded = 0").fetchall()
    assert len(rows) == 1
    assert rows[0]["filename"] == "broken.pdf"
    assert rows[0]["local_path"] is None


# ---------------------------------------------------------------------------
# inline data (no API call needed)
# ---------------------------------------------------------------------------


def test_inline_data(db_conn, tmp_path: Path) -> None:
    email_id = _insert_email(db_conn)
    content = b"inline-spreadsheet-data"

    mock_service = MagicMock()
    parts = [
        _make_part("data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", inline_data=content),
    ]
    count = process_attachments(
        service=mock_service,
        conn=db_conn,
        email_row_id=email_id,
        message_id="msg1",
        parts=parts,
        save_dir=tmp_path / "personal",
        allowed_extensions=[".xlsx"],
    )
    assert count == 1

    # The Gmail attachments API should NOT have been called for inline data
    mock_service.users().messages().attachments().get.assert_not_called()

    rows = db_conn.execute("SELECT * FROM attachments WHERE downloaded = 1").fetchall()
    assert len(rows) == 1
    saved_path = Path(rows[0]["local_path"])
    assert saved_path.exists()
    assert saved_path.read_bytes() == content
