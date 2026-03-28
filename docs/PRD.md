# fnsvr -- Product Requirements Document

## Overview

fnsvr is a local-first CLI tool for macOS that monitors multiple Gmail accounts for financial emails and ensures nothing important goes unreviewed. It runs as a background process via launchd, stores detections in local SQLite, and surfaces findings through macOS notifications, markdown digests, and an interactive review workflow.

## User Stories

### US-1: Multi-Account Gmail Scanning
**As** someone with 3+ Gmail accounts,
**I want** fnsvr to scan all of them on a schedule,
**So that** I don't have to manually check each inbox for financial emails.

**Acceptance Criteria:**
- Supports unlimited Gmail accounts, configured in YAML
- Each account authenticates independently via OAuth (gmail.readonly scope)
- Scans run via launchd on a configurable interval (default: every 4 hours)
- Scans also run on-demand via `fnsvr scan`
- First run supports a deep lookback (default: 90 days)
- Regular runs use a short lookback (default: 3 days)
- A single account can be scanned in isolation via `--account` flag
- Scan results are logged to both SQLite and a daily log file

### US-2: Financial Email Detection
**As** a user,
**I want** fnsvr to identify emails related to taxes, investments, banking, equity, and signatures,
**So that** I'm alerted to financially important emails I might otherwise miss.

**Acceptance Criteria:**
- Detects emails across five categories (see Detection Categories below)
- Detection uses case-insensitive substring matching on subject lines and sender addresses
- All patterns are defined in config.yaml (no hardcoded patterns in source)
- Each category has an assigned priority level (critical or high)
- Duplicate emails (same message_id + account) are not re-detected
- Each detection records: message_id, account, category, priority, subject, sender, date, snippet, matched pattern, attachment status

### US-3: Attachment Auto-Download
**As** a user,
**I want** fnsvr to automatically download PDF and spreadsheet attachments from detected financial emails,
**So that** I have local copies of important documents without manually downloading them.

**Acceptance Criteria:**
- Downloads attachments with configurable extension filter (default: .pdf, .xlsx, .xls, .csv, .doc, .docx)
- Saves to a local directory organized by account name
- Handles multipart/nested message structures
- Never overwrites existing files (appends counter suffix)
- Records each attachment in SQLite (filename, path, mime type, size, download status)
- Handles download failures gracefully (logs error, records failed status, continues scanning)

### US-4: macOS Notifications
**As** a user,
**I want** to receive macOS notifications when financial emails are detected,
**So that** I'm immediately aware of important items without checking the terminal.

**Acceptance Criteria:**
- Sends native macOS notification via osascript for each new detection
- Critical items use a distinct notification sound (default: "Submarine")
- High-priority items use a softer sound (default: "Pop")
- When detections exceed a batch threshold (default: 5), sends a single summary notification instead
- Notifications can be disabled via config
- Fails silently on non-macOS platforms (logs a debug message)

### US-5: Markdown Digest
**As** a user,
**I want** a periodic summary of detected financial emails,
**So that** I can review everything in one place and confirm nothing was missed.

**Acceptance Criteria:**
- Generates a markdown-formatted digest with:
  - Summary counts by priority, category, and account
  - Emails grouped by category (most urgent categories first)
  - Each email showing subject, sender, date, account, priority, preview snippet, review status
  - Action Required section listing unreviewed critical items
- Default digest covers the last 7 days
- Custom lookback via `--days` flag
- `--unreviewed` flag shows all unreviewed items regardless of date
- `--no-save` flag prints to stdout without saving
- Saved digests go to a configurable directory
- Optional auto-copy to an Obsidian vault path (configurable, off by default in example config)
- Weekly digest auto-generated via a separate launchd plist (Mondays 8am)

### US-6: Interactive Review
**As** a user,
**I want** to mark detected emails as reviewed with optional notes,
**So that** I have an auditable record of what I've acted on.

**Acceptance Criteria:**
- `fnsvr review` enters an interactive loop showing each unreviewed item
- Each item displays: priority, category, subject, sender, date, account, attachment status, preview
- User can: [y] mark reviewed (with optional notes), [n] skip, [q] quit, [a] mark all remaining
- Filterable by `--category` and `--account`
- `--mark-all` flag for bulk review without interactive prompt
- Review status and notes are persisted in SQLite

### US-7: Quick Stats
**As** a user,
**I want** a quick terminal summary of my detection history,
**So that** I can see at a glance whether anything needs attention.

**Acceptance Criteria:**
- `fnsvr stats` outputs total tracked, unreviewed count, breakdown by category and priority
- Fast (reads from SQLite, no Gmail API calls)
- Clean terminal output, no markdown

### US-8: Config Initialization
**As** a new user,
**I want** a single command to set up fnsvr,
**So that** I can get started quickly without manually creating directories and files.

**Acceptance Criteria:**
- `fnsvr init` creates `~/.fnsvr/` directory
- Copies `config.example.yaml` to `~/.fnsvr/config.yaml`
- Creates `~/.fnsvr/credentials/` directory
- Refuses to overwrite existing config unless `--force` is passed
- Prints next-step instructions (edit config, run setup)

### US-9: OAuth Account Setup
**As** a user,
**I want** a guided OAuth flow for each Gmail account,
**So that** I can authenticate without manually managing tokens.

**Acceptance Criteria:**
- `fnsvr setup <account_name>` initiates OAuth for the named account
- Opens a browser for Google sign-in
- Stores token locally with 600 permissions (owner-only)
- Refreshes expired tokens automatically on subsequent scans
- Provides clear error messages if credentials file is missing or account isn't configured
- Lists available accounts if the specified one isn't found

## Detection Categories

| Category Key | Label | Priority | What It Catches |
|-------------|-------|----------|----------------|
| `tax_documents` | Tax Documents (K1s, 1099s, W-2s) | critical | K1 schedules, 1099 variants, W-2s, 1098s, 5498s, tax statements |
| `signature_requests` | Documents Requiring Signature | critical | DocuSign, HelloSign/Dropbox Sign, Adobe Sign, PandaDoc, SignNow, Ironclad, Juro |
| `equity_grants` | Equity & Options Grant Notices | critical | Carta, stock options, RSUs, vesting, 409A, ESPP, cap table updates |
| `brokerage_statements` | Brokerage & Investment Statements | high | Account/monthly/quarterly statements, trade confirmations, dividends, margin calls |
| `bank_statements` | Bank Statements & Wire Confirmations | high | Wire transfers, ACH, bank statements, large transaction alerts |

Each category defines both `subject_patterns` (matched against email subjects) and `sender_patterns` (matched against From addresses). Matching is case-insensitive substring search. Subject patterns are evaluated before sender patterns. First match wins.

## Non-Functional Requirements

### NFR-1: Security
- Gmail API scope MUST be gmail.readonly -- no write access under any circumstances
- OAuth tokens stored with 600 file permissions
- Credentials directory must be in .gitignore
- No email content (beyond subject/snippet) is stored
- No data transmitted to external services

### NFR-2: Performance
- Regular scan (3-day lookback, 100 emails/account, 3 accounts) should complete in under 60 seconds
- Pattern matching should be negligible (pre-compiled regex)
- SQLite queries should be indexed appropriately

### NFR-3: Reliability
- Scan errors for one account should not block scanning of other accounts
- Attachment download failures should not block email detection
- Token refresh failures should produce clear error messages
- All errors logged to daily log files

### NFR-4: Portability
- macOS is the primary target (notifications, launchd)
- Core scanning, detection, storage, and digest generation should work on any OS
- Platform-specific code (notifications, scheduling) should be isolated in dedicated modules

## Out of Scope for v0.1

- GUI or web interface
- Outlook / Microsoft Graph API support
- IMAP support
- AI/LLM-based classification
- Email sending or modification
- Cloud sync or multi-device support
- Mobile notifications (push, SMS, etc.)
- Encryption at rest for the SQLite database
