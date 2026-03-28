# fnsvr -- Technical Specification

## 1. System Architecture

```
                    launchd (every 4h)
                          |
                     fnsvr scan
                          |
           +--------------+--------------+
           |              |              |
      Gmail Acct 1   Gmail Acct 2   Gmail Acct N
      (read-only)    (read-only)    (read-only)
           |              |              |
           +------+-------+------+------+
                  |              |
             detector.py    downloader.py
           (pattern match)  (attachments)
                  |              |
                  +------+-------+
                         |
                    storage.py
                     (SQLite)
                         |
              +----------+----------+
              |          |          |
         notifier.py  digest.py  reviewer.py
         (osascript)  (markdown)  (interactive)
```

All modules communicate through the SQLite database and config dict. There is no event bus, no message queue, no shared mutable state beyond the DB connection.

## 2. Module Specifications

### 2.1 config.py -- Configuration

**Responsibilities:**
- Load and validate config.yaml
- Resolve paths (expand ~, env vars)
- Create required directories
- Copy example config on `fnsvr init`

**Key Functions:**

```python
def get_config_dir() -> Path:
    """Return ~/.fnsvr or FNSVR_CONFIG_DIR env override."""

def get_config_path() -> Path:
    """Return path to active config.yaml."""

def load_config(config_path: Path | None = None) -> dict:
    """Load, validate, return config dict. Raises FileNotFoundError or ValueError."""

def resolve_path(path_str: str) -> Path:
    """Expand ~ and $ENV_VARS in path strings."""

def ensure_dirs(config: dict) -> None:
    """Create all data directories from config.paths."""

def init_config(force: bool = False) -> Path:
    """Create ~/.fnsvr/ and copy config.example.yaml. Returns path to new config."""
```

**Validation Rules:**
- Required top-level keys: accounts, paths, categories, scan
- At least one account must be configured
- All path values must be non-empty strings

**Config Dir:**
- Default: `~/.fnsvr/`
- Override: `FNSVR_CONFIG_DIR` environment variable
- Credential files are relative to config dir

### 2.2 detector.py -- Pattern Matching

**Responsibilities:**
- Compile regex patterns from config categories
- Match email subject/sender against compiled patterns
- Return match result with category, priority, label, matched pattern

**Key Types:**

```python
@dataclass
class DetectionMatch:
    category: str       # e.g. "tax_documents"
    priority: str       # "critical" | "high"
    label: str          # Human-readable, e.g. "Tax Documents (K1s, 1099s, W-2s)"
    matched_pattern: str # e.g. "subject:k\\-1" or "sender:docusign"

@dataclass
class CompiledCategory:
    key: str
    label: str
    priority: str
    subject_patterns: list[re.Pattern]
    sender_patterns: list[re.Pattern]
```

**Key Functions:**

```python
def compile_patterns(categories: dict) -> list[CompiledCategory]:
    """Pre-compile all patterns from config. Called once per scan run."""

def match_email(subject: str, sender: str, patterns: list[CompiledCategory]) -> DetectionMatch | None:
    """Test subject patterns first, then sender patterns. First match wins. Returns None if no match."""
```

**Pattern Matching Rules:**
- All patterns are wrapped in `re.escape()` (literal substring match, not regex)
- Case-insensitive (`re.IGNORECASE`)
- Subject patterns checked before sender patterns
- Categories checked in config definition order
- First match wins (no multi-category assignment)

**This module must be pure functions with zero side effects.** It does not touch the database, network, or filesystem. This makes it trivially testable.

### 2.3 storage.py -- SQLite Database

**Responsibilities:**
- Initialize database schema
- CRUD for detected_emails, attachments, scan_log
- Query helpers for review, digest, and stats

**Database Location:** `~/.fnsvr/data/fnsvr.db`

**Schema:**

```sql
CREATE TABLE detected_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_email TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    subject TEXT,
    sender TEXT,
    date_received TEXT,          -- ISO 8601
    snippet TEXT,                -- First 500 chars of email body preview
    matched_pattern TEXT,        -- What triggered the detection
    has_attachments INTEGER DEFAULT 0,
    notified INTEGER DEFAULT 0,
    reviewed INTEGER DEFAULT 0,
    notes TEXT,                  -- User notes from review
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(message_id, account_email)
);

CREATE TABLE attachments (
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

CREATE TABLE scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    account_email TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    emails_scanned INTEGER DEFAULT 0,
    emails_detected INTEGER DEFAULT 0,
    attachments_downloaded INTEGER DEFAULT 0,
    errors TEXT,
    status TEXT DEFAULT 'running'   -- running | completed | completed_with_errors
);
```

**Indexes:**
- `idx_emails_account` on `detected_emails(account_email)`
- `idx_emails_category` on `detected_emails(category)`
- `idx_emails_priority` on `detected_emails(priority)`
- `idx_emails_reviewed` on `detected_emails(reviewed)`
- `idx_emails_date` on `detected_emails(date_received)`

**Pragmas:**
- `journal_mode=WAL` (safe concurrent reads from digest/stats while scan writes)
- `foreign_keys=ON`

**Deduplication:** The `UNIQUE(message_id, account_email)` constraint handles dedup. `insert_email()` catches `IntegrityError` and returns `None` for duplicates.

### 2.4 scanner.py -- Gmail API Integration

**Responsibilities:**
- Authenticate with Gmail API via OAuth tokens
- Fetch message lists within date range
- Fetch full message details (headers, parts)
- Coordinate detection, attachment download, notification
- Log scan start/complete

**Key Functions:**

```python
def get_gmail_service(account: dict, config_dir: Path):
    """Build authenticated Gmail API service. Returns None on auth failure."""

def setup_oauth(account: dict, config_dir: Path) -> bool:
    """Run interactive OAuth flow. Opens browser. Stores token with 600 perms."""

def scan_account(
    account: dict,
    config: dict,
    conn: sqlite3.Connection,
    patterns: list[CompiledCategory],
    lookback_days: int,
    config_dir: Path,
) -> tuple[int, int, int]:
    """Scan one account. Returns (scanned, detected, downloaded)."""
```

**Gmail API Usage:**
- Scope: `https://www.googleapis.com/auth/gmail.readonly`
- List messages: `service.users().messages().list(userId="me", q=f"after:{date}", maxResults=N)`
- Get message: `service.users().messages().get(userId="me", id=msg_id, format="full")`
- Get attachment: `service.users().messages().attachments().get(userId="me", messageId=msg_id, id=att_id)`

**Error Handling:**
- Auth failures: log error, skip account, continue to next
- Individual message errors: log error, continue to next message
- Errors do not halt the scan -- they're collected and stored in scan_log

**Token Management:**
- Tokens stored at path specified in config (relative to config_dir)
- Auto-refresh if expired with valid refresh_token
- If refresh fails, log error and prompt user to re-run `fnsvr setup`

### 2.5 downloader.py -- Attachment Downloads

**Responsibilities:**
- Download attachments from Gmail API
- Save to local filesystem organized by account
- Handle multipart/nested MIME structures
- Record in database

**Key Functions:**

```python
def download_attachment(service, message_id: str, attachment_id: str,
                        filename: str, save_dir: Path) -> tuple[str, int]:
    """Download one attachment. Returns (local_path, size_bytes)."""

def process_attachments(service, conn, email_row_id: int, message_id: str,
                        parts: list[dict], save_dir: Path,
                        allowed_extensions: list[str]) -> int:
    """Process all attachments for an email. Returns download count. Recursive for multipart."""
```

**File Safety:**
- Filenames sanitized (non-alphanumeric replaced with `_`)
- No overwrites -- counter suffix appended if file exists
- Failed downloads recorded with `downloaded=0` in database

**Directory Structure:** `~/.fnsvr/data/attachments/<account_name>/`

### 2.6 notifier.py -- macOS Notifications

**Responsibilities:**
- Send native macOS notifications via osascript
- Batch notifications when volume is high
- Fail silently on non-macOS

**Key Functions:**

```python
def notify(title: str, message: str, subtitle: str = "", sound: str = "Pop") -> None:
    """Send one macOS notification. No-op on non-macOS."""

def notify_batch_summary(account_name: str, detections: list[dict]) -> None:
    """Send summary notification for many detections."""

def notify_digest_ready(digest_path: str, item_count: int) -> None:
    """Notify that a digest was generated."""
```

**Platform Detection:** Check `platform.system() == "Darwin"`. Skip with debug log on other platforms.

### 2.7 digest.py -- Markdown Digest Generator

**Responsibilities:**
- Generate markdown digests from database queries
- Save to filesystem
- Optionally copy to Obsidian vault

**Key Functions:**

```python
def generate_digest(emails: list[dict], title: str) -> str:
    """Generate markdown string from email list."""

def save_digest(digest_content: str, config: dict) -> Path:
    """Save digest to configured path. Copy to Obsidian if configured. Returns save path."""
```

**Digest Structure:**
1. Title + generation timestamp
2. Summary: total count, by priority, by account
3. Emails grouped by category (order: signature_requests, tax_documents, equity_grants, brokerage_statements, bank_statements)
4. Each email: subject, from, date, account, priority, attachment status, snippet, notes
5. Action Required section: unreviewed critical items listed

**Category Display Order (most urgent first):**
1. Signature Requests
2. Tax Documents
3. Equity & Options
4. Brokerage Statements
5. Bank Statements & Wires

### 2.8 reviewer.py -- Interactive Review

**Responsibilities:**
- Display unreviewed items one at a time
- Accept user input to mark reviewed, skip, quit, or bulk-mark
- Persist review status and notes

**Key Functions:**

```python
def review_interactive(conn: sqlite3.Connection, emails: list[dict]) -> int:
    """Run interactive review loop. Returns count of items reviewed."""
```

**Interaction Model:**
- Display one item with full details
- Prompt: `[y] mark reviewed  [n] skip  [q] quit  [a] mark all remaining`
- On `y`: optional notes prompt, then mark reviewed in DB
- On `a`: bulk mark all remaining as "Bulk reviewed"

### 2.9 cli.py -- Click CLI

**Responsibilities:**
- Define all user-facing commands
- Wire modules together
- Handle argument parsing and error display

**Commands:** See CLAUDE.md for full command list and flags.

**Entry Point:** `fnsvr = "fnsvr.cli:main"` in pyproject.toml

## 3. Config Schema

File: `~/.fnsvr/config.yaml` (copied from `config.example.yaml`)

```yaml
accounts:                          # List of Gmail accounts
  - name: string                   # Short identifier (e.g. "personal")
    email: string                  # Gmail address
    credentials_file: string       # Path to OAuth client credentials JSON (relative to config dir)
    token_file: string             # Path to store OAuth token (relative to config dir)

paths:
  database: string                 # Path to SQLite DB (~ expanded)
  attachments: string              # Path for downloaded files
  digests: string                  # Path for saved digests
  logs: string                     # Path for log files

categories:                        # Detection categories
  <category_key>:                  # e.g. tax_documents
    label: string                  # Human-readable label
    priority: string               # "critical" | "high" | "medium" | "low"
    subject_patterns: list[string] # Strings to match in subjects
    sender_patterns: list[string]  # Strings to match in senders

notifications:
  enabled: bool                    # Default true
  batch_threshold: int             # Group notifications above this count
  critical_sound: string           # macOS sound name
  normal_sound: string             # macOS sound name

digest:
  obsidian_copy: bool              # Copy digests to Obsidian vault
  obsidian_path: string            # Path to Obsidian vault directory

scan:
  initial_lookback_days: int       # Days back for --initial (default 90)
  regular_lookback_days: int       # Days back for regular scan (default 3)
  max_results_per_scan: int        # Gmail API max results per account (default 100)
  attachment_extensions: list[str] # File extensions to download
```

## 4. launchd Configuration

Two plist files in `launchd/`:

### com.fnsvr.scan.plist
- Runs `fnsvr scan` every 4 hours (StartInterval: 14400)
- RunAtLoad: true (scans on login)
- WorkingDirectory: ~/.fnsvr
- Logs to ~/.fnsvr/data/logs/

### com.fnsvr.digest.plist
- Runs `fnsvr digest` every Monday at 8:00 AM
- StartCalendarInterval: Weekday=1, Hour=8, Minute=0
- Logs to ~/.fnsvr/data/logs/

**Installation:**
```bash
cp launchd/*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.fnsvr.scan.plist
launchctl load ~/Library/LaunchAgents/com.fnsvr.digest.plist
```

**Note:** The plist ProgramArguments must point to the fnsvr executable in the user's venv or pip install location. Users will need to update this path.

## 5. Packaging

**pyproject.toml** using setuptools:
- Package in `src/fnsvr/`
- Entry point: `fnsvr = "fnsvr.cli:main"`
- Dependencies: google-api-python-client, google-auth-httplib2, google-auth-oauthlib, PyYAML, click
- Dev dependencies: pytest, pytest-cov, ruff
- Python >=3.11

**Installation:**
```bash
pip install -e ".[dev]"   # Development
pip install fnsvr          # From PyPI (future)
```

## 6. Testing Strategy

**Unit tests (required for v0.1):**
- `test_detector.py` -- Pattern compilation, subject matching, sender matching, case insensitivity, no-match, empty patterns, match priority order
- `test_storage.py` -- DB init, insert, dedup, unreviewed queries, mark reviewed, stats, account filtering
- `test_config.py` -- Config loading, validation errors, path resolution, missing file handling
- `test_digest.py` -- Digest generation with empty list, single item, multiple categories, unreviewed action section

**Integration tests (future):**
- End-to-end scan with mocked Gmail API
- CLI command smoke tests

**Test Approach:**
- Use `tempfile.mktemp()` for test databases
- No Gmail API mocking in v0.1 unit tests (test pure logic only)
- detector.py and storage.py are the highest-value test targets

## 7. Error Handling Philosophy

- **Scan-level errors** (auth failure, API quota): Log, skip account, continue to others
- **Message-level errors** (parse failure, missing headers): Log, skip message, continue scan
- **Attachment errors** (download failure): Log, record failure in DB, continue
- **Config errors** (missing file, bad YAML): Fail fast with clear error message
- **Notification errors** (osascript failure): Log warning, never block scan

The general principle: **scanning should never fail silently, but should also never halt entirely.** Errors are collected, logged, and stored in scan_log for later inspection.
