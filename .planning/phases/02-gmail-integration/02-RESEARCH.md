# Phase 2: Gmail Integration - Research

**Researched:** 2026-03-28
**Domain:** Gmail API integration (OAuth, message scanning, attachment downloading)
**Confidence:** HIGH

## Summary

Phase 2 connects the Foundation modules (config, storage, detector) to real Gmail data via the Gmail API. The three pillars are: (1) OAuth authentication using InstalledAppFlow with browser-based consent, (2) message scanning with date-filtered queries and pattern matching, and (3) attachment downloading with recursive MIME traversal. All Google client libraries are mature, well-documented, and the patterns are well-established for desktop/CLI apps.

The key technical risks are: OAuth token lifecycle management (especially the 7-day expiry trap in Testing mode), Gmail API date filter timezone ambiguity (solved by using epoch seconds), and nested multipart MIME structures that require recursive traversal. Error isolation per account is architecturally simple but must be deliberate -- a try/except boundary around each account's scan loop.

**Primary recommendation:** Build scanner.py as the orchestration layer (auth + scan + detect + download per account), with downloader.py as a focused helper for attachment retrieval. Keep the OAuth flow in scanner.py since `fnsvr setup` needs direct access to credential management.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Browser-based OAuth flow using google-auth-oauthlib's InstalledAppFlow (opens browser, captures token via localhost redirect)
- gmail.readonly scope exclusively -- no write access under any circumstances
- Tokens stored locally with 600 file permissions (os.chmod)
- Auto-refresh expired tokens using google.auth.transport.requests.Request
- Failed refresh produces clear error directing user to re-run `fnsvr setup <account>`
- Each account authenticates independently via its own credentials/token files
- Use Gmail API messages.list with `q=f"after:{epoch_timestamp}"` for date filtering (epoch timestamps, not date strings)
- Fetch full message details (format="full") for header extraction and attachment detection
- Extract subject from headers, sender from "From" header
- Run each email through detector.match_email(), store matches via storage.insert_email()
- Scan errors for one account must not block scanning of other accounts
- Every scan logged via storage.insert_scan_log/update_scan_log
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | `fnsvr setup <account>` initiates browser-based OAuth flow | InstalledAppFlow.from_client_secrets_file + run_local_server(port=0) |
| AUTH-02 | OAuth uses gmail.readonly scope exclusively | Single scope string: `https://www.googleapis.com/auth/gmail.readonly` |
| AUTH-03 | OAuth tokens stored with 600 file permissions | os.chmod(token_path, 0o600) after writing token JSON |
| AUTH-04 | Expired tokens auto-refresh without user intervention | Credentials.refresh(google.auth.transport.requests.Request()) before building service |
| AUTH-05 | Failed token refresh produces clear error directing re-run | Catch google.auth.exceptions.RefreshError, format user-facing message |
| SCAN-01 | `fnsvr scan` scans all accounts with 3-day default lookback | Loop accounts, compute epoch timestamp for N days ago, pass to messages.list q param |
| SCAN-02 | `fnsvr scan --initial` for 90-day deep lookback | Use config["scan"]["initial_lookback_days"] for lookback calculation |
| SCAN-03 | `fnsvr scan --days N` for custom lookback | Accept integer, override default lookback |
| SCAN-04 | `fnsvr scan --account <name>` for single account | Filter config["accounts"] list by name match |
| SCAN-05 | Scan errors for one account do not block others | try/except around each account's scan_account() call |
| SCAN-06 | Every scan logged with timing, counts, errors, status | insert_scan_log at start, update_scan_log at end with results |
| ATT-01 | Detected emails with PDF/spreadsheet attachments auto-downloaded | After detection match, pass message parts to process_attachments |
| ATT-02 | Downloads filtered by configurable extension list | Check filename extension against config["scan"]["attachment_extensions"] |
| ATT-03 | Files saved to ~/.fnsvr/data/attachments/<account_name>/ | Build path from config paths + account name |
| ATT-04 | Existing files never overwritten (counter suffix) | Check Path.exists() in loop, append _N suffix |
| ATT-05 | Failed downloads logged and recorded but don't block scan | try/except per attachment, record downloaded=0 in DB |
</phase_requirements>

## Standard Stack

### Core (already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-api-python-client | >=2.100.0 | Gmail API access | Official Google client. Provides `build("gmail", "v1", credentials=creds)` service objects |
| google-auth-oauthlib | >=1.1.0 | OAuth browser flow | Provides `InstalledAppFlow.from_client_secrets_file()` + `run_local_server()` |
| google-auth-httplib2 | >=0.1.1 | HTTP transport | Required by google-api-python-client for authorized HTTP requests |
| google-auth | (transitive) | Token management | Provides `google.auth.transport.requests.Request` for token refresh and `google.auth.exceptions.RefreshError` |

### Supporting (stdlib only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| base64 | stdlib | Attachment decoding | `base64.urlsafe_b64decode()` for Gmail attachment data |
| json | stdlib | Token file I/O | Read/write OAuth token JSON files |
| os | stdlib | File permissions | `os.chmod(path, 0o600)` for token security |
| time | stdlib | Epoch timestamps | `int(time.time())` for Gmail query date filters |
| re | stdlib | Filename sanitization | `re.sub(r'[^a-zA-Z0-9._-]', '_', filename)` |
| datetime | stdlib | Scan logging | ISO 8601 timestamps for scan_log entries |
| logging | stdlib | Error/info logging | Standard Python logging for scan progress and errors |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual token JSON I/O | google.oauth2.credentials.Credentials.to_json() | to_json() returns a string; manual JSON gives more control over file structure. Either works. |
| base64.urlsafe_b64decode | Standard base64.b64decode | Gmail API returns URL-safe base64; must use urlsafe variant |

**Installation:** No new packages needed. All dependencies already declared in pyproject.toml.

## Architecture Patterns

### Module Structure
```
src/fnsvr/
  scanner.py           # OAuth auth + scan orchestration (NEW)
  downloader.py        # Attachment downloading (NEW)
  config.py            # (EXISTS) load_config, get_config_dir, resolve_path
  storage.py           # (EXISTS) init_db, insert_email, insert_scan_log, update_scan_log
  detector.py          # (EXISTS) compile_patterns, match_email
```

### Pattern 1: OAuth Token Lifecycle
**What:** Load token from file -> check validity -> refresh if expired -> build service
**When to use:** Every `get_gmail_service()` call

```python
# Source: Google official oauth-installed docs + google.oauth2.credentials docs
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service(account: dict, config_dir: Path):
    """Build authenticated Gmail API service. Returns None on auth failure."""
    token_path = config_dir / account["token_file"]
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Rewrite token with fresh access_token
            token_path.write_text(creds.to_json())
            os.chmod(str(token_path), 0o600)
        except Exception:
            # Refresh failed -- token revoked or expired beyond repair
            return None

    if not creds or not creds.valid:
        return None  # Need setup_oauth() first

    return build("gmail", "v1", credentials=creds)
```

### Pattern 2: OAuth Setup Flow
**What:** Interactive browser-based consent flow for initial token acquisition
**When to use:** `fnsvr setup <account>` command

```python
def setup_oauth(account: dict, config_dir: Path) -> bool:
    """Run interactive OAuth flow. Opens browser. Stores token with 600 perms."""
    creds_path = config_dir / account["credentials_file"]
    token_path = config_dir / account["token_file"]

    if not creds_path.exists():
        return False  # No client credentials file

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)  # Opens browser, random port

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    os.chmod(str(token_path), 0o600)
    return True
```

### Pattern 3: Per-Account Error Isolation
**What:** Wrap each account scan in try/except so one failure does not block others
**When to use:** The top-level scan-all-accounts loop

```python
def scan_all(config: dict, conn, patterns, lookback_days: int, config_dir: Path):
    results = []
    for account in config["accounts"]:
        try:
            scanned, detected, downloaded = scan_account(
                account, config, conn, patterns, lookback_days, config_dir
            )
            results.append((account["name"], scanned, detected, downloaded, None))
        except Exception as exc:
            results.append((account["name"], 0, 0, 0, str(exc)))
    return results
```

### Pattern 4: Epoch Timestamp Date Filter
**What:** Convert lookback_days to epoch seconds for Gmail query
**When to use:** Building the `q` parameter for messages.list

```python
import time

def build_query(lookback_days: int) -> str:
    epoch = int(time.time()) - (lookback_days * 86400)
    return f"after:{epoch}"
```

### Pattern 5: Recursive MIME Part Traversal
**What:** Walk the payload.parts tree to find attachments at any nesting depth
**When to use:** Processing message parts for attachment detection and download

```python
def walk_parts(parts: list[dict] | None) -> list[dict]:
    """Recursively yield all leaf parts from a MIME tree."""
    if not parts:
        return []
    result = []
    for part in parts:
        if part.get("parts"):
            result.extend(walk_parts(part["parts"]))
        else:
            result.append(part)
    return result
```

### Pattern 6: Header Extraction
**What:** Gmail returns headers as a list of {"name": ..., "value": ...} dicts
**When to use:** Extracting Subject, From, Date from message payload

```python
def get_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name from Gmail API headers list."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""
```

### Anti-Patterns to Avoid
- **Global Gmail service object:** Each account has its own credentials. Build per-account services, never share.
- **Catching all exceptions silently:** Log every error with account context. The scan_log table is the audit trail.
- **Using date strings in Gmail queries:** `after:2024/01/15` uses Gmail's internal timezone (Pacific). Always use epoch seconds.
- **Downloading from all emails:** Only download attachments from emails that matched a detection pattern. This is both more efficient and more targeted.
- **Blocking on attachment failure:** A failed download must never prevent the next email from being scanned.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth browser flow | Custom HTTP server for callback | `InstalledAppFlow.run_local_server(port=0)` | Handles redirect URI, CSRF tokens, port selection automatically |
| Token refresh | Manual HTTP token endpoint calls | `Credentials.refresh(Request())` | Handles token endpoint URL, client secret injection, error handling |
| Gmail API request auth | Manual Authorization header injection | `build("gmail", "v1", credentials=creds)` | Automatic token injection, retry on 401 |
| Base64 URL-safe decoding | Manual character replacement | `base64.urlsafe_b64decode()` | Gmail API uses URL-safe base64 (`-_` not `+/`); stdlib handles padding |
| Token serialization | Custom JSON format | `Credentials.to_json()` / `from_authorized_user_file()` | Official format includes all required fields (refresh_token, token_uri, client_id, client_secret) |

**Key insight:** The entire OAuth lifecycle is handled by google-auth and google-auth-oauthlib. The only manual work is file I/O for token persistence and chmod for permissions.

## Common Pitfalls

### Pitfall 1: Testing Mode 7-Day Token Expiry
**What goes wrong:** Refresh tokens expire after 7 days and users must re-authenticate constantly.
**Why it happens:** GCP projects default to "Testing" publishing status. In Testing mode, refresh tokens for non-profile scopes (like gmail.readonly) expire after 7 days.
**How to avoid:** Document in setup instructions that the GCP project must be set to "Production" publishing status in the OAuth consent screen settings. For gmail.readonly scope, Google will require a verification review for Production status.
**Warning signs:** Users report "Token has been expired or revoked" errors exactly 7 days after setup.

### Pitfall 2: Gmail Date Filter Timezone Ambiguity
**What goes wrong:** Emails from the boundary day are missed or duplicated.
**Why it happens:** Gmail's `after:YYYY/MM/DD` filter uses Pacific timezone internally. A query meant for "last 3 days" can miss emails depending on the user's timezone.
**How to avoid:** Use epoch seconds: `after:{int(time.time()) - (days * 86400)}`. This is timezone-unambiguous.
**Warning signs:** Users in Eastern/Central timezones report missing recent emails.

### Pitfall 3: Attachment Data in Body vs Separate Request
**What goes wrong:** Code expects attachment data inline in the message but gets None.
**Why it happens:** Gmail API returns attachment data inline only for small attachments. For larger attachments, the `body` contains an `attachmentId` but no `data` field. A separate `attachments().get()` call is required.
**How to avoid:** Always check: if `body.get("data")` exists, use it directly. If `body.get("attachmentId")` exists, make a separate API call.
**Warning signs:** Small attachments download fine but PDFs and spreadsheets silently fail.

### Pitfall 4: Nested Multipart MIME
**What goes wrong:** Attachments inside nested multipart/mixed or multipart/related parts are missed.
**Why it happens:** Email MIME structure can be deeply nested. A flat iteration over `payload["parts"]` misses attachments nested in sub-parts.
**How to avoid:** Use recursive traversal (see Pattern 5 above). Walk the entire parts tree.
**Warning signs:** Some emails show has_attachments=True but no attachments are downloaded.

### Pitfall 5: Missing Token Fields After Refresh
**What goes wrong:** After refreshing, the rewritten token file is missing the refresh_token.
**Why it happens:** `Credentials.to_json()` includes all fields, but some older code patterns manually construct the token dict and forget to preserve the refresh_token.
**How to avoid:** Always use `creds.to_json()` for serialization. It preserves refresh_token, token_uri, client_id, and client_secret.
**Warning signs:** Token works for one session but fails on the next run.

### Pitfall 6: File Permission Race Condition
**What goes wrong:** Token file briefly exists with default permissions before chmod.
**Why it happens:** write_text() creates the file with umask-default permissions, then chmod follows.
**How to avoid:** This is acceptable for a single-user local-first tool. The window is microseconds. If paranoid, use os.open() with mode flags, but this is overkill for v0.1.
**Warning signs:** None in practice for this use case.

### Pitfall 7: Gmail API Rate Limits
**What goes wrong:** API calls fail with 429 Too Many Requests.
**Why it happens:** Gmail API has a per-user rate limit of 250 quota units per second. messages.list costs 5 units, messages.get costs 5 units, attachments.get costs 5 units.
**How to avoid:** The scan runs at most a few hundred messages every 4 hours. Rate limits are unlikely to be hit in normal use. If they are, the google-api-python-client's built-in exponential backoff handles retries automatically.
**Warning signs:** HttpError 429 in scan logs.

## Code Examples

### Complete OAuth Setup Flow
```python
# Source: Google OAuth for Installed Applications guide
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def setup_oauth(account: dict, config_dir: Path) -> bool:
    """Run interactive OAuth flow for one account."""
    creds_path = config_dir / account["credentials_file"]
    token_path = config_dir / account["token_file"]

    if not creds_path.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {creds_path}\n"
            f"Download OAuth client credentials from Google Cloud Console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    os.chmod(str(token_path), 0o600)
    return True
```

### Message Scanning with Pagination
```python
# Source: Gmail API messages.list documentation
def fetch_message_ids(service, query: str, max_results: int) -> list[str]:
    """Fetch all message IDs matching query, handling pagination."""
    message_ids = []
    page_token = None

    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": min(max_results, 500)}
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        messages = response.get("messages", [])
        message_ids.extend(msg["id"] for msg in messages)

        if len(message_ids) >= max_results:
            message_ids = message_ids[:max_results]
            break

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return message_ids
```

### Attachment Download with Fallback
```python
# Source: Gmail API attachments.get documentation
import base64

def download_attachment(
    service, message_id: str, attachment_id: str, filename: str, save_dir: Path
) -> tuple[str, int]:
    """Download one attachment. Returns (local_path, size_bytes)."""
    response = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    data = base64.urlsafe_b64decode(response["data"])
    safe_name = sanitize_filename(filename)
    save_path = unique_path(save_dir / safe_name)
    save_path.write_bytes(data)
    return str(save_path), len(data)


def sanitize_filename(filename: str) -> str:
    """Replace non-alphanumeric chars (except . _ -) with underscore."""
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", filename)


def unique_path(path: Path) -> Path:
    """Append counter suffix if file exists. Never overwrites."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OAuth out-of-band (OOB) flow | `run_local_server()` with localhost redirect | Google deprecated OOB in 2022 | Desktop apps MUST use localhost redirect, not copy-paste codes |
| Date strings in Gmail query | Epoch seconds in Gmail query | Always available, but under-documented | Eliminates timezone ambiguity |
| Manual httplib2 transport | google-auth handles transport automatically | google-api-python-client v2+ | Just pass credentials to `build()` |

**Deprecated/outdated:**
- `run_console()` method on InstalledAppFlow: Deprecated since OOB flow was removed. Always use `run_local_server()`.
- Manual token endpoint HTTP calls: Unnecessary. `Credentials.refresh()` handles everything.

## Open Questions

1. **Pagination strategy for max_results_per_scan**
   - What we know: Config default is 100, Gmail API maxResults cap is 500 per page. messages.list returns only IDs (lightweight).
   - What's unclear: Whether to respect max_results_per_scan strictly (truncate at 100) or use it as a soft cap.
   - Recommendation: Treat as hard cap. Most scans cover 3 days across personal accounts, well under 100 messages. The 90-day --initial scan might exceed 100, so pagination is needed.

2. **Credential file distribution model**
   - What we know: STATE.md notes "Embed OAuth client credentials in package (standard for desktop apps per RFC 8252)". CONTEXT.md says each account has its own credentials_file.
   - What's unclear: Whether one shared credentials.json ships with the package or users bring their own GCP project.
   - Recommendation: For v0.1, users bring their own credentials.json (downloaded from their GCP Console). Document this in setup instructions. Embedding credentials is a Phase 4/distribution concern.

3. **has_attachments detection**
   - What we know: storage.insert_email takes has_attachments as a flag.
   - What's unclear: Should has_attachments reflect "email has ANY attachments" or "email has attachments matching our extension filter"?
   - Recommendation: Set has_attachments=1 if the email has any parts with a filename. The extension filter only applies to downloading, not detection. This matches user expectations ("this email had attachments").

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.0 (installed via `pip install -e ".[dev]"`) |
| Config file | pyproject.toml (ruff config present; pytest uses defaults) |
| Quick run command | `pytest tests/test_scanner.py tests/test_downloader.py -x` |
| Full suite command | `pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | setup_oauth opens browser flow | unit (mock InstalledAppFlow) | `pytest tests/test_scanner.py::test_setup_oauth -x` | Wave 0 |
| AUTH-02 | Only gmail.readonly scope used | unit (assert SCOPES constant) | `pytest tests/test_scanner.py::test_scopes_readonly -x` | Wave 0 |
| AUTH-03 | Token stored with 600 permissions | unit (mock + check chmod) | `pytest tests/test_scanner.py::test_token_permissions -x` | Wave 0 |
| AUTH-04 | Expired token auto-refreshes | unit (mock Credentials) | `pytest tests/test_scanner.py::test_token_refresh -x` | Wave 0 |
| AUTH-05 | Failed refresh shows clear error | unit (mock RefreshError) | `pytest tests/test_scanner.py::test_refresh_failure_message -x` | Wave 0 |
| SCAN-01 | Scan all accounts, 3-day default | unit (mock Gmail service) | `pytest tests/test_scanner.py::test_scan_all_default -x` | Wave 0 |
| SCAN-02 | --initial uses 90-day lookback | unit (check query string) | `pytest tests/test_scanner.py::test_initial_lookback -x` | Wave 0 |
| SCAN-03 | --days N custom lookback | unit (check query string) | `pytest tests/test_scanner.py::test_custom_lookback -x` | Wave 0 |
| SCAN-04 | --account filters to single | unit (check account filtering) | `pytest tests/test_scanner.py::test_single_account -x` | Wave 0 |
| SCAN-05 | One account error does not block others | unit (mock exception on one account) | `pytest tests/test_scanner.py::test_error_isolation -x` | Wave 0 |
| SCAN-06 | Scan logged with timing and counts | unit (check insert/update_scan_log calls) | `pytest tests/test_scanner.py::test_scan_logging -x` | Wave 0 |
| ATT-01 | Detected emails' attachments downloaded | unit (mock process_attachments) | `pytest tests/test_downloader.py::test_download_detected -x` | Wave 0 |
| ATT-02 | Extension filter applied | unit | `pytest tests/test_downloader.py::test_extension_filter -x` | Wave 0 |
| ATT-03 | Saved to account subdirectory | unit | `pytest tests/test_downloader.py::test_save_path -x` | Wave 0 |
| ATT-04 | No overwrite, counter suffix | unit (tmp_path) | `pytest tests/test_downloader.py::test_no_overwrite -x` | Wave 0 |
| ATT-05 | Failed download recorded, scan continues | unit (mock download error) | `pytest tests/test_downloader.py::test_download_failure -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_scanner.py tests/test_downloader.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scanner.py` -- covers AUTH-01 through AUTH-05, SCAN-01 through SCAN-06
- [ ] `tests/test_downloader.py` -- covers ATT-01 through ATT-05
- [ ] Both test files need Gmail API mocking (unittest.mock.patch for google API calls, InstalledAppFlow, Credentials)
- [ ] conftest.py may need new fixtures: mock_gmail_service, mock_credentials, sample_message_payload

## Sources

### Primary (HIGH confidence)
- [Google OAuth for Installed Applications](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html) - InstalledAppFlow usage, token lifecycle
- [google.oauth2.credentials docs](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.credentials.html) - Credentials class, refresh(), to_json(), from_authorized_user_file()
- [Gmail API messages.list reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list) - Query params, pagination, maxResults
- [Gmail API attachments.get reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments) - Attachment retrieval by ID
- [Google OAuth Testing vs Production](https://developers.google.com/identity/protocols/oauth2) - 7-day token expiry in Testing mode

### Secondary (MEDIUM confidence)
- [Gmail API search operators](https://developers.google.com/gmail/api/guides/filtering) - Query syntax including epoch timestamp support for after:/before:
- [Gmail API pagination guide](https://googleapis.github.io/google-api-python-client/docs/pagination.html) - nextPageToken handling pattern

### Tertiary (LOW confidence)
- Community forums confirming multipart MIME recursive traversal patterns (multiple sources agree, elevated to MEDIUM)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in pyproject.toml, official Google docs are definitive
- Architecture: HIGH - tech spec defines module contracts, patterns are well-established for Gmail API desktop apps
- Pitfalls: HIGH - 7-day token expiry and timezone issues are widely documented; MIME nesting is a known complexity
- OAuth flow: HIGH - InstalledAppFlow.run_local_server() is the canonical approach, OOB deprecated

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable APIs, unlikely to change)
