---
phase: 02-gmail-integration
verified: 2026-03-28T20:30:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run fnsvr setup <account> with real Google Cloud credentials"
    expected: "Browser opens, user authenticates, token file written to disk with ls -la showing -rw------- permissions"
    why_human: "OAuth browser flow requires real credentials and cannot be exercised in an automated environment"
  - test: "Run fnsvr scan after setup with a Gmail account containing financial emails"
    expected: "Financial emails detected, attachments downloaded to ~/.fnsvr/data/attachments/<account_name>/, scan progress printed to terminal"
    why_human: "Requires live Gmail API connection and real email data"
---

# Phase 2: Gmail Integration Verification Report

**Phase Goal:** Users can authenticate Gmail accounts and scan them for financial emails with attachments downloaded automatically
**Verified:** 2026-03-28
**Status:** PASSED
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | setup_oauth opens browser-based OAuth flow and stores token with 600 permissions | VERIFIED | `scanner.py:58-63` calls `InstalledAppFlow.run_local_server(port=0)`, writes token, calls `os.chmod(str(token_path), 0o600)`. Repeated at refresh path line 94. Tests `test_setup_oauth` and `test_token_permissions` assert mode == 0o600. |
| 2 | get_gmail_service loads token, auto-refreshes if expired, returns None on auth failure | VERIFIED | `scanner.py:88-108` loads creds, calls `creds.refresh(Request())` on expired+refresh_token, catches `RefreshError` and returns None. Tests `test_token_refresh` and `test_refresh_failure_message` pass. |
| 3 | scan_account fetches messages within date range, runs detector, stores matches | VERIFIED | `scanner.py:237-286` calls `build_query` (epoch-based), `fetch_message_ids`, iterates messages, calls `detector.match_email`, calls `storage.insert_email` on match. Test `test_scan_logging` confirms scanned=1, detected=1. |
| 4 | scan_all wraps each account in try/except so one failure does not block others | VERIFIED | `scanner.py:365-373` wraps `scan_account` call in try/except, logs error, appends error tuple, continues. Test `test_error_isolation` confirms 2 results with first having error string and second having no error. |
| 5 | Every scan is logged with start time, completion time, counts, errors, and status | VERIFIED | `scanner.py:235,313-322` calls `storage.insert_scan_log` at start and `storage.update_scan_log` with completed_at, emails_scanned, emails_detected, attachments_downloaded, errors, status. Test `test_scan_logging` queries DB and asserts all fields. |
| 6 | Detected emails with PDF/spreadsheet attachments are downloaded automatically | VERIFIED | `scanner.py:290-302` calls `downloader.process_attachments` after detection match. Test `test_scan_account_downloads_attachments` asserts downloaded=1 and file exists on disk. |
| 7 | Downloads are filtered by configurable extension list | VERIFIED | `downloader.py:133-134` checks `Path(filename).suffix.lower() not in allowed_extensions`. Test `test_extension_filter` passes [".pdf"] and confirms .jpg part skipped, only .pdf downloaded. |
| 8 | Existing files are never overwritten (counter suffix appended) | VERIFIED | `downloader.py:24-40` `unique_path` increments counter until non-existing candidate found. Test `test_no_overwrite` confirms original preserved and new file saved as `test_1.pdf`. |
| 9 | Failed downloads are logged and recorded in DB but do not block scanning | VERIFIED | `downloader.py:170-183` catches Exception per attachment, logs error, inserts DB row with downloaded=0. Test `test_download_failure` confirms count=0, no exception raised, DB row with downloaded=0 and local_path=None. |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/fnsvr/scanner.py` | OAuth auth + scan orchestration | VERIFIED | 376 lines, exports 7 public functions: setup_oauth, get_gmail_service, get_header, build_query, fetch_message_ids, scan_account, scan_all. Full type hints and docstrings on all public functions. |
| `tests/test_scanner.py` | Unit tests for AUTH and SCAN requirements | VERIFIED | 546 lines, 21 test functions covering AUTH-01 through AUTH-05, SCAN-01 through SCAN-06, plus integration tests from Plan 03. All 21 pass. |
| `src/fnsvr/downloader.py` | Attachment downloading with MIME traversal | VERIFIED | 186 lines, exports 5 public functions: process_attachments, download_attachment, sanitize_filename, unique_path, walk_parts. |
| `tests/test_downloader.py` | Unit tests for ATT requirements | VERIFIED | 296 lines, 17 test functions covering ATT-01 through ATT-05. All 17 pass. |
| `src/fnsvr/cli.py` | Click CLI with setup and scan commands | VERIFIED | 131 lines, exports main, init, setup, scan commands. Entry point `fnsvr = "fnsvr.cli:main"` confirmed in pyproject.toml. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scanner.py` | `detector.py` | `detector.match_email` call | WIRED | Line 272: `match = detector.match_email(subject, sender, patterns)` |
| `scanner.py` | `storage.py` | `storage.insert_email` + `storage.insert_scan_log` + `storage.update_scan_log` | WIRED | Lines 235, 274, 313-322 |
| `downloader.py` | `storage.py` | `INSERT INTO attachments` | WIRED | Lines 161-168 (success) and 175-181 (failure) |
| `downloader.py` | Gmail API `attachments.get` | `service.users().messages().attachments().get()` | WIRED | Lines 82-86 in `download_attachment` |
| `cli.py` | `scanner.py` | `scanner.setup_oauth` call in setup command | WIRED | Line 68 |
| `cli.py` | `scanner.py` | `scanner.scan_all` call in scan command | WIRED | Line 108 |
| `scanner.py` | `downloader.py` | `downloader.process_attachments` in scan_account | WIRED | Line 294 |

---

### Requirements Coverage

All 17 requirement IDs declared across Plans 01, 02, and 03 are accounted for.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUTH-01 | 02-01, 02-03 | `fnsvr setup <account>` initiates OAuth flow | SATISFIED | `setup_oauth` in scanner.py; `setup` command in cli.py calls it; test_setup_oauth passes |
| AUTH-02 | 02-01 | OAuth uses gmail.readonly scope exclusively | SATISFIED | `SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]`; test_scopes_readonly asserts len==1 |
| AUTH-03 | 02-01 | Tokens stored with 600 permissions | SATISFIED | `os.chmod(str(token_path), 0o600)` called at lines 63 and 94; test_token_permissions asserts mode |
| AUTH-04 | 02-01 | Expired tokens auto-refresh | SATISFIED | `get_gmail_service` lines 90-95 refresh expired creds; test_token_refresh confirms |
| AUTH-05 | 02-01 | Failed refresh gives clear error directing to re-run setup | SATISFIED | RefreshError caught, `logger.error` message names account and re-run command; returns None; test_refresh_failure_message confirms |
| SCAN-01 | 02-01, 02-03 | `fnsvr scan` scans all accounts with 3-day default | SATISFIED | cli.py line 103 uses `regular_lookback_days` (3) as default; test_default_lookback via CliRunner passes |
| SCAN-02 | 02-01, 02-03 | `fnsvr scan --initial` for 90-day lookback | SATISFIED | cli.py line 101 uses `initial_lookback_days` (90); test_initial_flag via CliRunner passes |
| SCAN-03 | 02-01, 02-03 | `fnsvr scan --days N` for custom lookback | SATISFIED | cli.py line 99 uses provided days; test_days_flag via CliRunner passes |
| SCAN-04 | 02-01, 02-03 | `fnsvr scan --account <name>` for single account | SATISFIED | scan_all filters by account_filter; cli.py passes account_name; test_single_account confirms call_count==1 |
| SCAN-05 | 02-01 | One account error does not block others | SATISFIED | scan_all try/except loop; test_error_isolation confirms 2 results with different statuses |
| SCAN-06 | 02-01 | Every scan logged with timing, counts, errors, status | SATISFIED | insert_scan_log at start, update_scan_log at end with all fields; test_scan_logging queries DB |
| ATT-01 | 02-02, 02-03 | Detected emails with attachments auto-downloaded | SATISFIED | scan_account calls process_attachments after detection; test_scan_account_downloads_attachments confirms file on disk |
| ATT-02 | 02-02 | Downloads filtered by configurable extension list | SATISFIED | process_attachments checks suffix against allowed_extensions; test_extension_filter confirms |
| ATT-03 | 02-02 | Files saved to `~/.fnsvr/data/attachments/<account_name>/` with sanitized filenames | SATISFIED | save_dir = attachments_base / account["name"] in scanner.py; sanitize_filename in downloader.py; test_save_path confirms directory created |
| ATT-04 | 02-02 | Existing files never overwritten | SATISFIED | unique_path increments counter suffix; test_no_overwrite confirms original preserved |
| ATT-05 | 02-02 | Failed downloads logged and recorded in DB, non-blocking | SATISFIED | Per-attachment try/except in process_attachments; inserts downloaded=0 row; test_download_failure confirms |

**Orphaned requirements check:** No Phase 2 requirements in REQUIREMENTS.md are missing from the plan declarations. All 17 IDs (AUTH-01..05, SCAN-01..06, ATT-01..05) are claimed and verified.

---

### Anti-Patterns Found

No anti-patterns detected.

Scanned files: `src/fnsvr/scanner.py`, `src/fnsvr/downloader.py`, `src/fnsvr/cli.py`, `tests/test_scanner.py`, `tests/test_downloader.py`

- Zero TODO/FIXME/PLACEHOLDER/HACK comments
- No stub return values (`return null`, `return {}`, `return []` with no data population)
- No empty handlers
- No hardcoded static responses where real data is required
- All functions have substantive implementations

---

### Human Verification Required

#### 1. Browser OAuth Flow

**Test:** Install fnsvr (`pip install -e .`), configure a real credentials file from Google Cloud Console, then run `fnsvr setup personal`
**Expected:** Browser opens to Google OAuth consent screen. After granting read-only access, terminal shows "Authentication complete for 'personal'. Token saved." Token file exists at the configured path with `ls -la` showing `-rw-------` (600) permissions.
**Why human:** OAuth browser flow requires real Google Cloud project credentials and cannot be exercised in an automated test environment.

#### 2. Live Scan with Real Gmail

**Test:** After setup, run `fnsvr scan --initial` against a Gmail account known to contain financial emails (tax docs, brokerage statements, etc.)
**Expected:** Terminal shows scan progress, detected emails are printed with counts (scanned=N, detected=M, downloaded=K). PDF/spreadsheet attachments exist at `~/.fnsvr/data/attachments/<account_name>/`. SQLite DB contains rows in `detected_emails`, `attachments`, and `scan_log` tables.
**Why human:** Requires live Gmail API connection, real email data, and real attachment downloads.

#### 3. Token Expiry Auto-Refresh

**Test:** Allow an OAuth token to expire (or manually edit the expiry field to a past date), then run `fnsvr scan`
**Expected:** Scan proceeds normally without user intervention. Log shows "Token refreshed for <account>." at DEBUG level.
**Why human:** Requires an expired token and live Google OAuth token refresh endpoint.

---

### Gaps Summary

No gaps. All 9 observable truths are verified against actual code, all 5 required artifacts exist and are substantive, all 7 key links are wired, and all 17 requirement IDs are satisfied with evidence in the codebase.

**Test suite results:** 81/81 tests pass (38 from scanner+downloader, 43 from foundation modules). Zero regressions introduced.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
