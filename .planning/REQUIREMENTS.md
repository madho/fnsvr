# Requirements: fnsvr

**Defined:** 2026-03-28
**Core Value:** Financial emails with real deadlines and real dollar consequences must never go unnoticed, regardless of which inbox they landed in.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Configuration

- [x] **CFG-01**: User can run `fnsvr init` to create ~/.fnsvr/ directory and copy example config
- [x] **CFG-02**: User can define multiple Gmail accounts in config.yaml with name, email, credentials path, and token path
- [x] **CFG-03**: Config validates required top-level keys (accounts, paths, categories, scan) and rejects invalid YAML with clear error messages
- [x] **CFG-04**: All path values expand ~ and $ENV_VARS correctly
- [x] **CFG-05**: Config dir is overridable via FNSVR_CONFIG_DIR environment variable

### Authentication

- [ ] **AUTH-01**: User can run `fnsvr setup <account>` to initiate browser-based OAuth flow for a Gmail account (like gcloud auth login)
- [ ] **AUTH-02**: OAuth uses gmail.readonly scope exclusively -- no write access under any circumstances
- [ ] **AUTH-03**: OAuth tokens are stored locally with 600 file permissions (owner-only)
- [ ] **AUTH-04**: Expired tokens are auto-refreshed on subsequent scans without user intervention
- [ ] **AUTH-05**: Failed token refresh produces clear error message directing user to re-run `fnsvr setup`

### Detection

- [x] **DET-01**: Detector matches email subjects and senders against config-defined patterns using case-insensitive substring matching
- [x] **DET-02**: All detection patterns are config-driven in YAML -- zero hardcoded patterns in source code
- [x] **DET-03**: Detection covers 5 categories: tax_documents (critical), signature_requests (critical), equity_grants (critical), brokerage_statements (high), bank_statements (high)
- [x] **DET-04**: Subject patterns are checked before sender patterns; first match wins across categories
- [x] **DET-05**: Each detection records: message_id, account, category, priority, subject, sender, date, snippet, matched_pattern, attachment status
- [x] **DET-06**: Duplicate emails (same message_id + account_email) are not re-detected

### Scanning

- [ ] **SCAN-01**: User can run `fnsvr scan` to scan all configured accounts with 3-day default lookback
- [ ] **SCAN-02**: User can run `fnsvr scan --initial` for 90-day deep lookback on first run
- [ ] **SCAN-03**: User can run `fnsvr scan --days N` for custom lookback period
- [ ] **SCAN-04**: User can run `fnsvr scan --account <name>` to scan a single account
- [ ] **SCAN-05**: Scan errors for one account do not block scanning of other accounts
- [ ] **SCAN-06**: Every scan is logged with start time, completion time, emails scanned/detected, errors, and status

### Storage

- [x] **STOR-01**: SQLite database initializes with detected_emails, attachments, and scan_log tables
- [x] **STOR-02**: Database uses WAL journal mode for safe concurrent reads during writes
- [x] **STOR-03**: Tables are properly indexed (account, category, priority, reviewed, date_received)
- [x] **STOR-04**: No email content beyond subject, snippet (500 chars), and sender is stored

### Attachments

- [ ] **ATT-01**: Detected financial emails with PDF/spreadsheet attachments are auto-downloaded
- [ ] **ATT-02**: Downloads are filtered by configurable extension list (default: .pdf, .xlsx, .xls, .csv, .doc, .docx)
- [ ] **ATT-03**: Files are saved to ~/.fnsvr/data/attachments/<account_name>/ with sanitized filenames
- [ ] **ATT-04**: Existing files are never overwritten (counter suffix appended)
- [ ] **ATT-05**: Failed downloads are logged and recorded in database but do not block scanning

### Notifications

- [ ] **NOTF-01**: macOS native notification sent for each new detection via osascript
- [ ] **NOTF-02**: Critical items use "Submarine" sound; high-priority items use "Pop" sound
- [ ] **NOTF-03**: When detections exceed batch threshold (default: 5), a single summary notification is sent instead
- [ ] **NOTF-04**: Notifications can be disabled via config
- [ ] **NOTF-05**: Non-macOS platforms fail silently with debug log message

### Digest

- [ ] **DIG-01**: User can run `fnsvr digest` to generate markdown digest of last 7 days
- [ ] **DIG-02**: Digest includes summary counts by priority, category, and account
- [ ] **DIG-03**: Emails grouped by category in urgency order: signature requests, tax docs, equity, brokerage, bank
- [ ] **DIG-04**: Digest includes Action Required section listing unreviewed critical items
- [ ] **DIG-05**: User can customize lookback with `--days N` and filter with `--unreviewed`
- [ ] **DIG-06**: Digest can optionally auto-copy to Obsidian vault path (configurable, off by default)
- [ ] **DIG-07**: `--no-save` flag prints to stdout without saving to disk

### Review

- [ ] **REV-01**: User can run `fnsvr review` to enter interactive review loop showing each unreviewed item
- [ ] **REV-02**: Each item displays priority, category, subject, sender, date, account, attachment status, snippet
- [ ] **REV-03**: User can mark reviewed (with optional notes), skip, quit, or mark all remaining
- [ ] **REV-04**: Review is filterable by `--category` and `--account`
- [ ] **REV-05**: `--mark-all` flag for bulk review without interactive prompt
- [ ] **REV-06**: Review status and notes are persisted in SQLite with timestamps

### Stats

- [ ] **STAT-01**: User can run `fnsvr stats` for terminal summary of total tracked, unreviewed count, breakdown by category and priority
- [ ] **STAT-02**: Stats read from SQLite only -- no Gmail API calls

### Scheduling

- [ ] **SCHED-01**: launchd plist for scanning every 4 hours with RunAtLoad
- [ ] **SCHED-02**: launchd plist for weekly digest generation (Monday 8am)
- [ ] **SCHED-03**: Plists are generated dynamically with absolute binary paths (not static templates)
- [ ] **SCHED-04**: User can install/uninstall scheduling via CLI commands (not manual launchctl)

### Distribution

- [ ] **DIST-01**: Package installable via `pip install fnsvr` from PyPI
- [ ] **DIST-02**: Homebrew tap formula for `brew install fnsvr` single-command install
- [ ] **DIST-03**: Entry point `fnsvr` available on PATH after install

### Website

- [ ] **WEB-01**: Single-page landing site (fnsvr.com) in one self-contained index.html file
- [ ] **WEB-02**: Dark terminal aesthetic with monospace code, warm amber accents, under 30KB total
- [ ] **WEB-03**: Sections: hero, problem statement, 5-category feature grid, 3-step how-it-works, design principles, quick-start terminal block, footer
- [ ] **WEB-04**: No analytics, no tracking, no cookies, no JS frameworks
- [ ] **WEB-05**: Deployable to GitHub Pages or Vercel with zero build step

### Testing

- [x] **TEST-01**: Unit tests for detector.py -- pattern compilation, matching, case insensitivity, no-match, priority order
- [x] **TEST-02**: Unit tests for storage.py -- DB init, insert, dedup, queries, mark reviewed, stats
- [x] **TEST-03**: Unit tests for config.py -- loading, validation errors, path resolution, missing file handling
- [ ] **TEST-04**: Unit tests for digest.py -- empty list, single item, multiple categories, action section

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Platform Expansion

- **PLAT-01**: Linux notification support (notify-send or similar)
- **PLAT-02**: systemd timer as launchd alternative for Linux
- **PLAT-03**: Windows Task Scheduler support

### Email Providers

- **PROV-01**: Outlook / Microsoft Graph API support
- **PROV-02**: IMAP support for self-hosted email

### Advanced Features

- **ADV-01**: Rich/Textual for prettier terminal output
- **ADV-02**: macOS Keychain integration for token storage
- **ADV-03**: Incremental scanning via Gmail historyId (performance optimization)
- **ADV-04**: International financial institution pattern libraries
- **ADV-05**: Tax-season readiness reports

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| GUI or web dashboard | Terminal-native is the identity. Every competitor is GUI -- differentiation IS the terminal |
| AI/LLM classification | Adds latency, cloud dependency, non-determinism. Pattern matching is simple, auditable, fast |
| Email sending or modification | Read-only is a trust decision. Users with real assets verify this claim |
| Cloud sync or multi-device | Local-first is the point. Undermines core privacy value prop |
| Mobile notifications (push, SMS) | Requires a server component, violates local-first |
| Encryption at rest for SQLite | DB stores only subject/snippet/sender, not bodies or credentials. Threat model doesn't justify for v0.1 |
| Full email content storage | Privacy liability and storage concern. Subject + snippet + sender is enough |
| Shared OAuth app / auth relay | Requires a server and ongoing maintenance. Direct Google auth is simpler and more trustworthy |
| Real-time push scanning | Gmail API doesn't support true push to local apps. 4-hour polling is the right trade-off |
| Multi-user / team features | Personal tool. MIT license allows forking for team use |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | Phase 1 | Complete |
| CFG-02 | Phase 1 | Complete |
| CFG-03 | Phase 1 | Complete |
| CFG-04 | Phase 1 | Complete |
| CFG-05 | Phase 1 | Complete |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| DET-01 | Phase 1 | Complete |
| DET-02 | Phase 1 | Complete |
| DET-03 | Phase 1 | Complete |
| DET-04 | Phase 1 | Complete |
| DET-05 | Phase 1 | Complete |
| DET-06 | Phase 1 | Complete |
| SCAN-01 | Phase 2 | Pending |
| SCAN-02 | Phase 2 | Pending |
| SCAN-03 | Phase 2 | Pending |
| SCAN-04 | Phase 2 | Pending |
| SCAN-05 | Phase 2 | Pending |
| SCAN-06 | Phase 2 | Pending |
| STOR-01 | Phase 1 | Complete |
| STOR-02 | Phase 1 | Complete |
| STOR-03 | Phase 1 | Complete |
| STOR-04 | Phase 1 | Complete |
| ATT-01 | Phase 2 | Pending |
| ATT-02 | Phase 2 | Pending |
| ATT-03 | Phase 2 | Pending |
| ATT-04 | Phase 2 | Pending |
| ATT-05 | Phase 2 | Pending |
| NOTF-01 | Phase 3 | Pending |
| NOTF-02 | Phase 3 | Pending |
| NOTF-03 | Phase 3 | Pending |
| NOTF-04 | Phase 3 | Pending |
| NOTF-05 | Phase 3 | Pending |
| DIG-01 | Phase 3 | Pending |
| DIG-02 | Phase 3 | Pending |
| DIG-03 | Phase 3 | Pending |
| DIG-04 | Phase 3 | Pending |
| DIG-05 | Phase 3 | Pending |
| DIG-06 | Phase 3 | Pending |
| DIG-07 | Phase 3 | Pending |
| REV-01 | Phase 3 | Pending |
| REV-02 | Phase 3 | Pending |
| REV-03 | Phase 3 | Pending |
| REV-04 | Phase 3 | Pending |
| REV-05 | Phase 3 | Pending |
| REV-06 | Phase 3 | Pending |
| STAT-01 | Phase 3 | Pending |
| STAT-02 | Phase 3 | Pending |
| SCHED-01 | Phase 4 | Pending |
| SCHED-02 | Phase 4 | Pending |
| SCHED-03 | Phase 4 | Pending |
| SCHED-04 | Phase 4 | Pending |
| DIST-01 | Phase 4 | Pending |
| DIST-02 | Phase 4 | Pending |
| DIST-03 | Phase 4 | Pending |
| WEB-01 | Phase 5 | Pending |
| WEB-02 | Phase 5 | Pending |
| WEB-03 | Phase 5 | Pending |
| WEB-04 | Phase 5 | Pending |
| WEB-05 | Phase 5 | Pending |
| TEST-01 | Phase 1 | Complete |
| TEST-02 | Phase 1 | Complete |
| TEST-03 | Phase 1 | Complete |
| TEST-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 67 total
- Mapped to phases: 67
- Unmapped: 0

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after roadmap creation*
