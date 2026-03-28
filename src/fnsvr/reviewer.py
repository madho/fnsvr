"""Interactive review workflow for fnsvr."""
from __future__ import annotations

import logging
import sqlite3

from fnsvr import storage

log = logging.getLogger(__name__)


def format_email(email: sqlite3.Row, index: int, total: int) -> str:
    """Return a formatted string displaying one email for review."""
    attachments = "Yes" if email["has_attachments"] else "No"
    snippet = email["snippet"] if email["snippet"] else "(no preview)"
    return (
        f"--- [{index}/{total}] ---\n"
        f"Priority:    {email['priority']}\n"
        f"Category:    {email['category']}\n"
        f"Subject:     {email['subject']}\n"
        f"From:        {email['sender']}\n"
        f"Date:        {email['date_received']}\n"
        f"Account:     {email['account_name']}\n"
        f"Attachments: {attachments}\n"
        f"\n{snippet}\n"
    )


def review_interactive(conn: sqlite3.Connection, emails: list[sqlite3.Row]) -> int:
    """Run interactive review loop. Returns count of items reviewed."""
    if len(emails) == 0:
        print("No unreviewed items.")
        return 0

    print(f"Found {len(emails)} unreviewed item(s).\n")
    reviewed_count = 0

    try:
        for i, email in enumerate(emails):
            print(format_email(email, i + 1, len(emails)))
            while True:
                choice = input(
                    "[y] mark reviewed  [n] skip  [q] quit  [a] mark all remaining > "
                ).strip().lower()
                if choice == "y":
                    notes_input = input("Notes (Enter to skip): ").strip()
                    notes = notes_input if notes_input else None
                    storage.mark_reviewed(conn, email["id"], notes)
                    reviewed_count += 1
                    break
                elif choice == "n":
                    break
                elif choice == "q":
                    print(f"\nReviewed {reviewed_count} item(s).")
                    return reviewed_count
                elif choice == "a":
                    reviewed_count += mark_all(conn, emails[i:])
                    print(f"\nReviewed {reviewed_count} item(s).")
                    return reviewed_count
                else:
                    print("Unknown option. Try y/n/q/a.")
    except (KeyboardInterrupt, EOFError):
        print("\nReview cancelled.")
        return reviewed_count

    print(f"\nReviewed {reviewed_count} item(s).")
    return reviewed_count


def mark_all(
    conn: sqlite3.Connection,
    emails: list[sqlite3.Row],
    notes: str = "Bulk reviewed",
) -> int:
    """Mark all given emails as reviewed. Returns count of items marked."""
    count = 0
    for email in emails:
        storage.mark_reviewed(conn, email["id"], notes)
        count += 1
    return count
