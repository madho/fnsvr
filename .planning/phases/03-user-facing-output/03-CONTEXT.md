# Phase 3: User-Facing Output - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the four output modules (notifier.py, digest.py, reviewer.py, stats via cli.py) and wire them into the CLI. These modules consume data already stored in SQLite by the scanner -- they are independent read-side consumers of the detection database.

</domain>

<decisions>
## Implementation Decisions

### Notifications (notifier.py)
- macOS native notifications via osascript (subprocess call)
- Critical items use "Submarine" sound; high-priority use "Pop"
- Batch summary when detections exceed threshold (default: 5) -- single notification instead of N
- Notifications can be disabled via config (notifications.enabled: false)
- Non-macOS platforms fail silently with debug log message (check platform.system() == "Darwin")
- Called by scanner after detecting new emails (integrate into scan flow)

### Digest (digest.py)
- Generate markdown-formatted digest from SQLite queries
- Group emails by category in urgency order: signature_requests, tax_documents, equity_grants, brokerage_statements, bank_statements
- Include summary counts by priority, category, and account
- Action Required section listing unreviewed critical items
- Default lookback: 7 days. Customizable via --days flag
- --unreviewed flag shows all unreviewed regardless of date
- --no-save prints to stdout without saving
- Optional auto-copy to Obsidian vault path (configurable, off by default)
- Saved digests go to configurable directory (paths.digests in config)

### Review (reviewer.py)
- Interactive terminal loop showing each unreviewed item
- Each item: priority, category, subject, sender, date, account, attachment status, snippet
- User actions: [y] mark reviewed (with optional notes), [n] skip, [q] quit, [a] mark all remaining
- Filterable by --category and --account
- --mark-all flag for bulk review without interactive prompt
- Review status and notes persisted in SQLite (storage.mark_reviewed)

### Stats (via cli.py)
- Quick terminal summary: total tracked, unreviewed count, breakdown by category and priority
- Read-only SQLite queries (storage.get_stats) -- no Gmail API calls
- Clean terminal output, no markdown formatting

### CLI Integration
- Add commands: fnsvr digest, fnsvr review, fnsvr stats
- Wire notifier into scanner.scan_account() to notify on new detections

### Claude's Discretion
- Terminal formatting (colors, alignment, spacing)
- Notification text truncation for long subjects
- Digest markdown formatting details
- Stats output layout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- src/fnsvr/storage.py -- get_unreviewed(), mark_reviewed(), get_stats(), get_emails_by_date_range (may need to add)
- src/fnsvr/cli.py -- existing Click group with init, setup, scan commands
- src/fnsvr/config.py -- load_config() for notification/digest settings
- tests/conftest.py -- db_conn fixture, sample_config fixture

### Established Patterns
- Click CLI group pattern in cli.py
- Storage functions return sqlite3.Row objects (dict-like access)
- Config dict structure for notification/digest settings

### Integration Points
- notifier.py called from scanner.scan_account() after new detections
- digest.py reads from storage via SQL queries
- reviewer.py reads/writes storage via get_unreviewed/mark_reviewed
- All new commands added to cli.py Click group

</code_context>

<specifics>
## Specific Ideas

- Digest category display order is fixed: signature_requests first (most urgent), then tax_documents, equity_grants, brokerage_statements, bank_statements
- Review interactive loop should be simple input() based -- no curses or rich library needed
- Stats should be fast -- pure SQLite read, no computation

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>
