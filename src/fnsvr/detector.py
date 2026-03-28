"""Pattern matching engine for fnsvr. Pure functions, zero side effects.

This module decides which emails matter by matching subject and sender fields
against config-driven patterns. It uses plain substring matching (not regex)
with case-insensitive comparison. Subject patterns are checked before sender
patterns within each category, and the first match wins across all categories.

Imports: only ``dataclasses``. No I/O, no filesystem, no network, no database.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DetectionMatch:
    """Result of a successful pattern match.

    Attributes:
        category: Config key, e.g. "tax_documents".
        priority: "critical" or "high".
        label: Human-readable label from config.
        matched_pattern: "subject:<pattern>" or "sender:<pattern>".
    """

    category: str
    priority: str
    label: str
    matched_pattern: str


@dataclass
class CompiledCategory:
    """Pre-processed category with lowercased patterns for substring matching.

    Attributes:
        key: Config key, e.g. "tax_documents".
        label: Human-readable label from config.
        priority: Priority level from config.
        subject_patterns: Lowercased subject patterns for ``in`` matching.
        sender_patterns: Lowercased sender patterns for ``in`` matching.
    """

    key: str
    label: str
    priority: str
    subject_patterns: list[str]
    sender_patterns: list[str]


def compile_patterns(categories: dict) -> list[CompiledCategory]:
    """Convert config categories dict into a list of CompiledCategory.

    Patterns are lowercased once here so ``match_email`` can do simple ``in``
    checks without repeated case folding. Called once per scan run.

    Args:
        categories: The ``categories`` section of the fnsvr config dict.
            Keys are category identifiers, values have ``label``, ``priority``,
            ``subject_patterns``, and ``sender_patterns``.

    Returns:
        List of ``CompiledCategory`` in config definition order (dict insertion
        order, guaranteed in Python 3.7+).
    """
    compiled: list[CompiledCategory] = []
    for key, cat in categories.items():
        compiled.append(
            CompiledCategory(
                key=key,
                label=cat["label"],
                priority=cat["priority"],
                subject_patterns=[p.lower() for p in cat.get("subject_patterns", [])],
                sender_patterns=[p.lower() for p in cat.get("sender_patterns", [])],
            )
        )
    return compiled


def match_email(
    subject: str, sender: str, patterns: list[CompiledCategory]
) -> DetectionMatch | None:
    """Test an email against compiled patterns. First match wins.

    Subject patterns are checked before sender patterns within each category.
    Categories are checked in the order they appear in the compiled list (which
    preserves config definition order).

    Args:
        subject: Email subject line.
        sender: Email sender address or display name.
        patterns: Compiled categories from ``compile_patterns``.

    Returns:
        A ``DetectionMatch`` on the first hit, or ``None`` if nothing matches.
        This function has zero side effects.
    """
    subject_lower = subject.lower()
    sender_lower = sender.lower()

    for cat in patterns:
        for pattern in cat.subject_patterns:
            if pattern in subject_lower:
                return DetectionMatch(
                    category=cat.key,
                    priority=cat.priority,
                    label=cat.label,
                    matched_pattern=f"subject:{pattern}",
                )
        for pattern in cat.sender_patterns:
            if pattern in sender_lower:
                return DetectionMatch(
                    category=cat.key,
                    priority=cat.priority,
                    label=cat.label,
                    matched_pattern=f"sender:{pattern}",
                )
    return None
