"""Markdown digest generator for fnsvr."""
from __future__ import annotations

import logging
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from fnsvr import config as config_module

logger = logging.getLogger(__name__)

CATEGORY_ORDER = [
    "signature_requests",
    "tax_documents",
    "equity_grants",
    "brokerage_statements",
    "bank_statements",
]

CATEGORY_LABELS = {
    "signature_requests": "Signature Requests",
    "tax_documents": "Tax Documents",
    "equity_grants": "Equity & Options",
    "brokerage_statements": "Brokerage Statements",
    "bank_statements": "Bank Statements & Wires",
}


def generate_digest(emails: list[dict], title: str = "fnsvr Digest") -> str:
    """Generate a markdown digest from a list of email dicts.

    Takes email dicts (or sqlite3.Row objects with dict-like access).
    Returns a markdown string grouped by category in urgency order.
    """
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    if not emails:
        lines.append("No detections in this period.")
        return "\n".join(lines)

    # Summary section
    lines.append("## Summary")
    lines.append("")
    lines.append(f"**Total detections:** {len(emails)}")
    lines.append("")

    # By Priority
    priority_counts: Counter[str] = Counter()
    for email in emails:
        priority_counts[email["priority"]] += 1
    lines.append("**By Priority:**")
    for priority in ["critical", "high", "medium", "low"]:
        count = priority_counts.get(priority, 0)
        if count:
            lines.append(f"- {priority}: {count}")
    lines.append("")

    # By Account
    account_counts: Counter[str] = Counter()
    for email in emails:
        account_counts[email["account_name"]] += 1
    lines.append("**By Account:**")
    for account_name, count in sorted(account_counts.items()):
        lines.append(f"- {account_name}: {count}")
    lines.append("")

    # Group emails by category
    by_category: dict[str, list[dict]] = {}
    for email in emails:
        cat = email["category"]
        by_category.setdefault(cat, []).append(email)

    # Render each category in urgency order
    for cat in CATEGORY_ORDER:
        if cat not in by_category:
            continue
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"## {label}")
        lines.append("")
        for email in by_category[cat]:
            lines.append(f"### {email['subject']}")
            lines.append(f"- **From:** {email['sender']}")
            lines.append(f"- **Date:** {email['date_received']}")
            lines.append(f"- **Account:** {email['account_name']}")
            lines.append(f"- **Priority:** {email['priority']}")
            attachments = "Yes" if email.get("has_attachments") else "No"
            lines.append(f"- **Attachments:** {attachments}")
            snippet = email.get("snippet", "")
            if snippet:
                lines.append(f"- **Snippet:** {str(snippet)[:200]}")
            lines.append("")

    # Action Required section
    lines.append("## Action Required")
    lines.append("")
    action_items = [
        e for e in emails if not e.get("reviewed") and e.get("priority") == "critical"
    ]
    if action_items:
        for email in action_items:
            lines.append(
                f"- **{email['subject']}** ({email['account_name']}) -- {email['category']}"
            )
    else:
        lines.append("No critical unreviewed items.")
    lines.append("")

    return "\n".join(lines)


def save_digest(
    content: str, config: dict, no_save: bool = False
) -> Path | None:
    """Save digest to configured path. Optionally copy to Obsidian vault.

    If no_save is True, returns None (caller prints to stdout).
    Returns the primary save path on success.
    """
    if no_save:
        return None

    digests_path = config_module.resolve_path(config["paths"]["digests"])
    digests_path.mkdir(parents=True, exist_ok=True)

    filename = f"digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    save_path = digests_path / filename
    save_path.write_text(content, encoding="utf-8")
    logger.info("Digest saved to %s", save_path)

    # Obsidian copy
    digest_cfg = config.get("digest", {})
    if digest_cfg.get("obsidian_copy", False):
        obsidian_path = config_module.resolve_path(digest_cfg["obsidian_path"])
        obsidian_path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(save_path, obsidian_path / filename)
        logger.info("Digest copied to Obsidian vault: %s", obsidian_path / filename)

    return save_path
