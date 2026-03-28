"""Unit tests for fnsvr digest generation (TEST-04)."""
from __future__ import annotations

from fnsvr.digest import generate_digest


def make_email(**overrides: object) -> dict:
    """Create a test email dict mimicking sqlite3.Row dict access."""
    base: dict = {
        "id": 1,
        "message_id": "msg1",
        "account_name": "personal",
        "account_email": "test@gmail.com",
        "category": "tax_documents",
        "priority": "critical",
        "subject": "Your K-1 is ready",
        "sender": "tax@turbotax.com",
        "date_received": "2026-03-25",
        "snippet": "Your tax document is available",
        "matched_pattern": "subject:k-1",
        "has_attachments": 1,
        "notified": 0,
        "reviewed": 0,
        "notes": None,
        "created_at": "2026-03-25 10:00:00",
    }
    base.update(overrides)
    return base


def test_empty_digest() -> None:
    """Empty email list produces 'No detections' message."""
    result = generate_digest([])
    assert "No detections" in result
    assert "fnsvr Digest" in result


def test_single_email() -> None:
    """Single email renders correct markdown with subject, sender, category heading."""
    email = make_email()
    result = generate_digest([email])
    assert "## Tax Documents" in result
    assert "### Your K-1 is ready" in result
    assert "tax@turbotax.com" in result


def test_category_order() -> None:
    """Multiple categories render in CATEGORY_ORDER (urgency order)."""
    emails = [
        make_email(id=1, category="bank_statements", subject="Wire received"),
        make_email(id=2, category="signature_requests", subject="Sign this"),
        make_email(id=3, category="tax_documents", subject="Your 1099"),
    ]
    result = generate_digest(emails)
    sig_pos = result.index("## Signature Requests")
    tax_pos = result.index("## Tax Documents")
    bank_pos = result.index("## Bank Statements & Wires")
    assert sig_pos < tax_pos < bank_pos


def test_action_required_unreviewed() -> None:
    """Unreviewed critical email appears in Action Required section."""
    email = make_email(reviewed=0, priority="critical")
    result = generate_digest([email])
    action_section = result[result.index("## Action Required"):]
    assert "Your K-1 is ready" in action_section


def test_action_required_all_reviewed() -> None:
    """All reviewed critical emails produce 'No critical unreviewed items'."""
    email = make_email(reviewed=1, priority="critical")
    result = generate_digest([email])
    assert "No critical unreviewed items" in result


def test_summary_counts() -> None:
    """Summary counts by priority and account are correct."""
    emails = [
        make_email(id=1, priority="critical", account_name="personal"),
        make_email(id=2, priority="critical", account_name="work"),
        make_email(id=3, priority="high", account_name="personal"),
    ]
    result = generate_digest(emails)
    assert "**Total detections:** 3" in result
    assert "critical: 2" in result
    assert "high: 1" in result
    assert "personal: 2" in result
    assert "work: 1" in result
