# Phase 2: Gmail Integration - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement Gmail API integration: OAuth authentication flow (browser-based, like gcloud auth login), multi-account scanning with error isolation, attachment downloading with safe file handling. This phase connects the Foundation modules (config, storage, detector) to real Gmail data.

</domain>

<decisions>
## Implementation Decisions

### OAuth Authentication
- Browser-based OAuth flow using google-auth-oauthlib's InstalledAppFlow (opens browser, captures token via localhost redirect)
- gmail.readonly scope exclusively -- no write access under any circumstances
- Tokens stored locally with 600 file permissions (os.chmod)
- Auto-refresh expired tokens using google.auth.transport.requests.Request
- Failed refresh produces clear error directing user to re-run `fnsvr setup <account>`
- Each account authenticates independently via its own credentials/token files

### Scanning
- Use Gmail API messages.list with `q=f"after:{epoch_timestamp}"` for date filtering (epoch timestamps, not date strings -- avoids timezone ambiguity per research)
- Fetch full message details (format="full") for header extraction and attachment detection
- Extract subject from headers, sender from "From" header
- Run each email through detector.match_email(), store matches via storage.insert_email()
- Scan errors for one account must not block scanning of other accounts
- Every scan logged via storage.insert_scan_log/update_scan_log

### Attachments
- Download attachments from detected emails only (not all emails)
- Filter by configurable extension list from config (default: .pdf, .xlsx, .xls, .csv, .doc, .docx)
- Handle multipart/nested MIME structures recursively
- Sanitize filenames (non-alphanumeric replaced with underscore)
- Never overwrite existing files (append counter suffix: filename_1.pdf, filename_2.pdf)
- Failed downloads logged and recorded in DB but do not block scanning
- Save to ~/.fnsvr/data/attachments/<account_name>/

### Claude's Discretion
- Internal helper functions for parsing email headers/parts
- Error message formatting
- Logging format and verbosity
- Gmail API pagination strategy (single page vs multi-page)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- src/fnsvr/config.py -- load_config(), get_config_dir(), resolve_path(), ensure_dirs()
- src/fnsvr/storage.py -- init_db(), insert_email(), insert_scan_log(), update_scan_log()
- src/fnsvr/detector.py -- compile_patterns(), match_email()
- tests/conftest.py -- sample_config fixture, db_conn fixture

### Established Patterns
- Type hints on all function signatures
- Docstrings on all public functions
- No ORM -- raw sqlite3
- Config dict passed as parameter (not global state)
- Error handling: fail fast for config, resilient for scanning

### Integration Points
- scanner.py calls config.load_config() for account list and scan settings
- scanner.py calls detector.compile_patterns() once per scan run
- scanner.py calls storage.insert_email() for each detection
- scanner.py calls storage.insert_scan_log/update_scan_log for audit trail
- downloader.py calls Gmail API for attachment data
- downloader.py records in storage via attachments table

</code_context>

<specifics>
## Specific Ideas

- Research flagged: Gmail API date filter `after:` should use epoch timestamps (seconds since epoch) to avoid timezone ambiguity
- Research flagged: OAuth tokens in "Testing" mode expire after 7 days -- GCP project should be set to "Production" publishing status
- The `fnsvr setup` command should be part of cli.py but the OAuth flow logic lives in scanner.py
- scanner.py is the only "compound module" -- it orchestrates detector, downloader, and storage within a scan run

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>
