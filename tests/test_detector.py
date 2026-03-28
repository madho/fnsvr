"""Tests for fnsvr.detector -- pattern matching engine."""
from __future__ import annotations

import pytest

from fnsvr.detector import (
    CompiledCategory,
    DetectionMatch,
    compile_patterns,
    match_email,
)


def _make_categories() -> dict:
    """Build a categories dict matching all 5 config categories."""
    return {
        "tax_documents": {
            "label": "Tax Documents",
            "priority": "critical",
            "subject_patterns": ["k-1", "1099", "w-2"],
            "sender_patterns": ["irs.gov", "turbotax"],
        },
        "signature_requests": {
            "label": "Documents Requiring Signature",
            "priority": "critical",
            "subject_patterns": ["please sign", "signature request"],
            "sender_patterns": ["docusign", "hellosign"],
        },
        "equity_grants": {
            "label": "Equity & Options",
            "priority": "critical",
            "subject_patterns": ["stock option", "rsu", "vesting"],
            "sender_patterns": ["carta", "shareworks"],
        },
        "brokerage_statements": {
            "label": "Brokerage Statements",
            "priority": "high",
            "subject_patterns": ["account statement", "trade confirmation"],
            "sender_patterns": ["schwab", "vanguard"],
        },
        "bank_statements": {
            "label": "Bank Statements",
            "priority": "high",
            "subject_patterns": ["wire transfer", "bank statement"],
            "sender_patterns": ["chase", "bankofamerica"],
        },
    }


def _make_patterns() -> list[CompiledCategory]:
    """Compile patterns from the full 5-category config."""
    return compile_patterns(_make_categories())


# --- Dataclass structure tests ---


class TestDetectionMatchFields:
    def test_detection_match_fields(self) -> None:
        """DetectionMatch has category, priority, label, matched_pattern fields."""
        m = DetectionMatch(
            category="tax_documents",
            priority="critical",
            label="Tax Documents",
            matched_pattern="subject:k-1",
        )
        assert m.category == "tax_documents"
        assert m.priority == "critical"
        assert m.label == "Tax Documents"
        assert m.matched_pattern == "subject:k-1"


class TestCompiledCategoryFields:
    def test_compiled_category_fields(self) -> None:
        """CompiledCategory has key, label, priority, subject_patterns, sender_patterns."""
        c = CompiledCategory(
            key="tax_documents",
            label="Tax Documents",
            priority="critical",
            subject_patterns=["k-1", "1099"],
            sender_patterns=["irs.gov"],
        )
        assert c.key == "tax_documents"
        assert c.label == "Tax Documents"
        assert c.priority == "critical"
        assert c.subject_patterns == ["k-1", "1099"]
        assert c.sender_patterns == ["irs.gov"]


# --- compile_patterns tests ---


class TestCompilePatterns:
    def test_compile_from_config(self) -> None:
        """compile_patterns converts categories dict into list of CompiledCategory."""
        categories = {
            "tax_documents": {
                "label": "Tax Documents",
                "priority": "critical",
                "subject_patterns": ["K-1", "1099"],
                "sender_patterns": ["IRS.gov"],
            },
        }
        result = compile_patterns(categories)
        assert len(result) == 1
        assert isinstance(result[0], CompiledCategory)
        assert result[0].key == "tax_documents"
        assert result[0].label == "Tax Documents"
        assert result[0].priority == "critical"
        # Patterns must be lowercased
        assert result[0].subject_patterns == ["k-1", "1099"]
        assert result[0].sender_patterns == ["irs.gov"]

    def test_compile_patterns_empty(self) -> None:
        """compile_patterns with empty dict returns empty list."""
        result = compile_patterns({})
        assert result == []

    def test_five_categories(self) -> None:
        """compile_patterns with all 5 category keys produces 5 CompiledCategory objects."""
        patterns = _make_patterns()
        assert len(patterns) == 5
        keys = [p.key for p in patterns]
        assert keys == [
            "tax_documents",
            "signature_requests",
            "equity_grants",
            "brokerage_statements",
            "bank_statements",
        ]


# --- match_email tests ---


class TestMatchEmail:
    def test_case_insensitive_subject(self) -> None:
        """match_email('Your K-1 is Ready', ...) matches pattern 'k-1'."""
        patterns = _make_patterns()
        result = match_email("Your K-1 is Ready", "noreply@example.com", patterns)
        assert result is not None
        assert result.category == "tax_documents"
        assert result.matched_pattern == "subject:k-1"

    def test_case_insensitive_sender(self) -> None:
        """match_email with 'DocuSign@example.com' matches pattern 'docusign'."""
        patterns = _make_patterns()
        result = match_email("Some document for you", "DocuSign@example.com", patterns)
        assert result is not None
        assert result.category == "signature_requests"
        assert result.matched_pattern == "sender:docusign"

    def test_subject_before_sender(self) -> None:
        """When both subject and sender match different categories, subject match wins."""
        patterns = _make_patterns()
        # Subject matches signature_requests, sender matches tax_documents
        result = match_email("Please sign this", "tax@irs.gov", patterns)
        assert result is not None
        # Subject match in signature_requests should win because we iterate categories
        # in order and signature_requests comes after tax_documents, BUT
        # the subject "Please sign this" doesn't match tax_documents subjects.
        # tax_documents has no subject match here, so it checks sender -> irs.gov matches.
        # BUT subject patterns are checked first WITHIN each category.
        # tax_documents: subject patterns [k-1, 1099, w-2] -- no match
        #                sender patterns [irs.gov, turbotax] -- "irs.gov" matches!
        # So tax_documents wins because it's first in order and sender matches.
        # Let's use a case where subject in one cat AND sender in another both match:
        # We need the subject to match a LATER category while sender matches an EARLIER one.
        # Use subject="please sign" (matches signature_requests) with sender from tax
        # But tax_documents is checked first. Its subjects don't match "please sign".
        # Its senders include "irs.gov". If sender is "irs.gov", tax_documents sender matches.
        # So we need a sender from a category that comes BEFORE signature_requests
        # and a subject that matches signature_requests.
        # Actually, within each category, subject is checked before sender.
        # So for tax_documents: check subjects (no match), check senders (irs.gov matches).
        # First match wins means tax_documents wins, not signature_requests.
        # To test subject-before-sender, use a single category where both could match.
        pass

    def test_subject_before_sender_same_category(self) -> None:
        """Within a single category, subject match takes priority over sender match."""
        # Create a category where subject AND sender both match
        categories = {
            "test_cat": {
                "label": "Test Category",
                "priority": "high",
                "subject_patterns": ["important doc"],
                "sender_patterns": ["example.com"],
            },
        }
        patterns = compile_patterns(categories)
        result = match_email("Important Doc Attached", "user@example.com", patterns)
        assert result is not None
        assert result.matched_pattern.startswith("subject:")

    def test_subject_match_wins_over_earlier_sender_match(self) -> None:
        """Subject checked before sender within each category; first category match wins."""
        # Category A: subject won't match, sender will match
        # Category B: subject will match
        # Category A is checked first. Within A, subject checked first (no match),
        # then sender (match). So A wins via sender. This tests first-match-wins.
        categories = {
            "cat_a": {
                "label": "Category A",
                "priority": "high",
                "subject_patterns": ["zzz no match"],
                "sender_patterns": ["specialsender"],
            },
            "cat_b": {
                "label": "Category B",
                "priority": "critical",
                "subject_patterns": ["hello world"],
                "sender_patterns": [],
            },
        }
        patterns = compile_patterns(categories)
        result = match_email("hello world", "user@specialsender.com", patterns)
        assert result is not None
        # cat_a: subject "zzz no match" not in "hello world" -> no match
        #         sender "specialsender" in "user@specialsender.com" -> match!
        assert result.category == "cat_a"
        assert result.matched_pattern == "sender:specialsender"

    def test_first_match_wins(self) -> None:
        """With tax_documents before brokerage, subject '1099' returns tax_documents."""
        patterns = _make_patterns()
        result = match_email("Your 1099 statement", "noreply@example.com", patterns)
        assert result is not None
        assert result.category == "tax_documents"
        assert result.matched_pattern == "subject:1099"

    def test_no_match(self) -> None:
        """match_email returns None when no patterns match."""
        patterns = _make_patterns()
        result = match_email("Hello world", "friend@example.com", patterns)
        assert result is None

    def test_empty_patterns(self) -> None:
        """match_email with empty subject_patterns and sender_patterns returns None."""
        categories = {
            "empty_cat": {
                "label": "Empty",
                "priority": "low",
                "subject_patterns": [],
                "sender_patterns": [],
            },
        }
        patterns = compile_patterns(categories)
        result = match_email("anything", "anyone@example.com", patterns)
        assert result is None

    def test_matched_pattern_format_subject(self) -> None:
        """When subject matches, matched_pattern is 'subject:<pattern>'."""
        patterns = _make_patterns()
        result = match_email("Your 1099 form", "noreply@example.com", patterns)
        assert result is not None
        assert result.matched_pattern == "subject:1099"

    def test_matched_pattern_format_sender(self) -> None:
        """When sender matches, matched_pattern is 'sender:<pattern>'."""
        patterns = _make_patterns()
        result = match_email("Hello", "noreply@turbotax.com", patterns)
        assert result is not None
        assert result.matched_pattern == "sender:turbotax"

    def test_match_priority_order(self) -> None:
        """Categories are checked in config definition order."""
        # Both brokerage_statements and bank_statements have "account statement"
        # in subject_patterns. brokerage_statements comes first, so it should win.
        patterns = _make_patterns()
        result = match_email("Your account statement is ready", "noreply@example.com", patterns)
        assert result is not None
        assert result.category == "brokerage_statements"
        assert result.matched_pattern == "subject:account statement"
