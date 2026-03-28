# Domain Pitfalls

**Domain:** Local-first CLI email monitoring (Gmail API, OAuth, SQLite, macOS launchd)
**Researched:** 2026-03-28

## Critical Pitfalls

Mistakes that cause broken installs, silent data loss, or complete scan failures.

### Pitfall 1: OAuth Consent Screen Left in "Testing" Mode -- Tokens Expire Every 7 Days

**What goes wrong:** Google Cloud projects with OAuth consent screen publishing status set to "Testing" cause refresh tokens to expire after exactly 7 days. Users set up fnsvr, it works for a week, then every account silently fails authentication. The tool appears broken with no obvious cause.

**Why it happens:** Developers create a GCP project, set up OAuth, and never change the publishing status from the default "Testing" to "Production." Google enforces a 7-day token lifetime for testing apps as a deliberate limitation.

**Consequences:** All scans fail after 7 days. Users must re-run `fnsvr setup` for every account weekly, which completely defeats the "set it and forget it" value proposition. Users will abandon the tool.

**Prevention:**
- Document prominently in setup instructions that the GCP project MUST be set to "Production" publishing status (this does NOT require Google verification for apps used only by the project owner)
- Add a check during `fnsvr setup` that warns if the token lacks a refresh_token or if the refresh_token is suspiciously short-lived
- Include a troubleshooting section specifically for "token expired after 7 days"
- Consider embedding client credentials in the distributed package (acceptable for desktop/installed apps per RFC 8252) so users never touch GCP console at all

**Detection:** Scan logs show auth failures starting exactly 7 days after setup. Multiple accounts fail simultaneously.

**Phase relevance:** Phase 1 (OAuth/Scanner). Must be addressed in initial architecture -- the decision about whether to embed credentials or require users to create GCP projects is foundational.

**Confidence:** HIGH -- well-documented Google behavior, multiple community reports.

**Sources:**
- [HomeSeer Forum: Refresh Token Expires in 7 Days](https://forums.homeseer.com/forum/internet-or-network-related-plug-ins/internet-or-network-discussion/ak-google-calendar-alexbk66/1545936-refresh-token-expires-in-7-days-if-oauth-consent-screen-publishing-status-is-testing)
- [Nango: Google OAuth invalid_grant](https://www.nango.dev/blog/google-oauth-invalid-grant-token-has-been-expired-or-revoked)
- [Google Cloud: Manage App Audience](https://support.google.com/cloud/answer/15549945?hl=en)

---

### Pitfall 2: launchd Runs Without User's Shell PATH -- fnsvr Binary Not Found

**What goes wrong:** launchd agents run outside any shell context. They do not load `.zshrc`, `.bash_profile`, or any shell configuration. The PATH is minimal (typically just `/usr/bin:/bin:/usr/sbin:/sbin`). If fnsvr is installed via pip or Homebrew, the binary likely lives in `/usr/local/bin`, `/opt/homebrew/bin`, or a virtualenv `bin/` -- none of which are in launchd's default PATH.

**Why it happens:** Developers test `fnsvr scan` in their terminal where PATH is fully configured, then write a plist that calls `fnsvr` by name. It works in the terminal but silently fails when launchd runs it because the binary cannot be found.

**Consequences:** Scheduled scans never execute. No notifications appear. The user assumes fnsvr is running but it has been silently failing since they loaded the plist. No errors appear anywhere the user would naturally look.

**Prevention:**
- Use absolute paths in plist ProgramArguments -- never rely on PATH resolution. The `fnsvr schedule` command should detect the actual binary path via `shutil.which("fnsvr")` or `sys.executable` and write it into the plist
- Set EnvironmentVariables in the plist to include the necessary PATH entries
- Never use tilde (`~`) in plist paths -- launchd does not expand it. Use full absolute paths
- Write launchd stdout/stderr to log files so failures are visible: `StandardOutPath` and `StandardErrorPath` keys in the plist
- The `fnsvr init` or `fnsvr schedule` command should generate plists dynamically with the correct paths for the user's system, not ship static plists

**Detection:** `launchctl list | grep fnsvr` shows the job but with a non-zero last exit status. Log files (if configured) show "command not found" or similar.

**Phase relevance:** Phase covering launchd integration. Must generate plists dynamically, not ship static templates.

**Confidence:** HIGH -- extremely well-documented macOS administration issue.

**Sources:**
- [Lucas Pinheiro: Where is my PATH, launchD?](https://lucaspin.medium.com/where-is-my-path-launchd-fc3fc5449864)
- [launchd.info Tutorial](https://launchd.info/)
- [Apple Developer Forums: Environment variables for launchctl](https://developer.apple.com/forums/thread/681550)

---

### Pitfall 3: Credential Distribution Model -- Users Cannot Create GCP Projects

**What goes wrong:** The PRD says "fnsvr setup opens a browser for Google OAuth (like gcloud auth login)" but gcloud works because Google distributes the client credentials embedded in the gcloud CLI. If fnsvr requires each user to create their own GCP project, navigate the Cloud Console, enable the Gmail API, create OAuth credentials, download `credentials.json`, and place it in `~/.fnsvr/` -- the target persona (busy founders, not daily coders) will not complete setup.

**Why it happens:** OAuth for desktop apps requires a client_id and client_secret, which come from a GCP project. The developer assumes users can create this themselves, but the GCP Console is hostile to non-developers.

**Consequences:** Massive drop-off at setup. The tool never gets used. The entire value proposition fails at the first step.

**Prevention:**
- Embed client credentials in the distributed fnsvr package. For "Desktop app" OAuth client types, the client_secret is not actually secret (per RFC 8252 and Google's own documentation). gcloud, many open-source tools, and Google's own Python quickstart examples do this
- Set the GCP project's consent screen to "Production" so tokens do not expire after 7 days
- If distributing credentials, add the OAuth consent screen's privacy policy URL pointing to fnsvr.com
- Alternative: provide a fnsvr.com web page that walks users through GCP project creation with screenshots, but this is strictly worse than embedding credentials

**Detection:** Users report they cannot get past setup. GitHub issues flood in about "credentials.json not found."

**Phase relevance:** Phase 1. This is the single most important architectural decision. Must be resolved before any OAuth code is written.

**Confidence:** HIGH -- Google's own documentation confirms desktop app secrets are not treated as confidential.

**Sources:**
- [googleapis/google-auth-library-nodejs Issue #959: Client secrets in desktop open-source apps](https://github.com/googleapis/google-auth-library-nodejs/issues/959)
- [Simon Willison: Google OAuth for a CLI application](https://til.simonwillison.net/googlecloud/google-oauth-cli-application)
- [Google: OAuth 2.0 for iOS & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)

---

### Pitfall 4: Gmail API Date Filter Timezone Ambiguity

**What goes wrong:** The Gmail API's `after:` search operator interprets dates differently depending on format. Google's documentation claims dates are interpreted as midnight PST, but community testing shows UTC behavior. When fnsvr uses `after:2026/03/25` for a 3-day lookback, the boundary could be off by up to 8 hours, causing emails to be missed or double-processed depending on the user's timezone.

**Why it happens:** The developer uses Python's `datetime.now()` to calculate the lookback date and formats it as `YYYY/MM/DD` in the query string. This introduces timezone ambiguity at the boundary.

**Consequences:** Emails received near midnight get missed on regular scans. The 3-day lookback window has ragged edges. Users in EST/CST/MST may miss emails that arrived late in their evening.

**Prevention:**
- Use epoch timestamps (seconds since 1970-01-01 UTC) in the `after:` query parameter instead of date strings. This eliminates all timezone ambiguity: `after:{int(timestamp)}`
- Add 24 hours of buffer to the lookback window (scan 4 days when config says 3) to ensure overlap. Deduplication via the UNIQUE constraint handles any double-detection
- Document that the deduplication guarantee makes overlapping scan windows safe and intentional

**Detection:** Users report missing emails that arrived in the evening. Comparing scan_log timestamps with email dates reveals gaps at day boundaries.

**Phase relevance:** Phase covering scanner.py. The query construction must use epoch timestamps from day one.

**Confidence:** MEDIUM -- documented inconsistency between Google's stated behavior and observed behavior. Using epoch timestamps eliminates the issue regardless.

**Sources:**
- [Google: Search and filter messages](https://developers.google.com/workspace/gmail/api/guides/filtering)
- [GitHub Issue #3290: Query mails after date returns results before this date](https://github.com/googleapis/google-api-nodejs-client/issues/3290)
- [Latenode: How to filter Gmail messages by date considering timezone differences](https://community.latenode.com/t/how-to-filter-gmail-messages-by-date-considering-timezone-differences/33720)

---

## Moderate Pitfalls

### Pitfall 5: SQLite WAL Mode Must Be Set Before Any Transactions Begin

**What goes wrong:** Python's `sqlite3` module in autocommit mode (the default before Python 3.12) implicitly starts a transaction on the first statement. Setting `PRAGMA journal_mode=WAL` while a transaction is active either silently fails or raises an error. The database stays in the default rollback journal mode, losing WAL's concurrency benefits.

**Why it happens:** The developer opens a connection, runs some setup queries, then sets WAL mode -- but the implicit transaction from the setup queries prevents the mode change.

**Prevention:**
- Set `PRAGMA journal_mode=WAL` as the very first statement after opening the connection, before any other queries
- Verify the return value: `cursor.execute("PRAGMA journal_mode=WAL")` returns `[('wal',)]` on success. If it returns `[('delete',)]`, the mode was not changed
- In Python 3.12+, use `sqlite3.connect(db, autocommit=True)` for the initial pragma, then switch to managed transactions
- Consider setting WAL mode once during `fnsvr init` database creation, not on every connection (WAL mode persists across connections)

**Detection:** `PRAGMA journal_mode;` returns `delete` instead of `wal`. Concurrent reads during scans may block or fail.

**Phase relevance:** Phase covering storage.py. Must be correct in the initial schema creation.

**Confidence:** HIGH -- documented SQLite behavior.

**Sources:**
- [SQLite WAL documentation](https://www.sqlite.org/wal.html)
- [TechNetExperts: Set SQLite WAL Mode in Python 3.12](https://www.technetexperts.com/python-sqlite-wal-autocommit-false/)

---

### Pitfall 6: Homebrew Formula Breaks on Python Upgrades

**What goes wrong:** When Homebrew upgrades Python (e.g., 3.11 to 3.12), the shebang in installed scripts points to the old Python path, which no longer exists. fnsvr stops working with "bad interpreter" errors. The launchd plist still points to the old binary path.

**Why it happens:** Homebrew manages a single Python version and upgrades it in-place. Scripts installed via pip or setuptools get shebangs pointing to the specific Python version path.

**Prevention:**
- Use Homebrew's `virtualenv_install_with_resources` pattern in the formula, which creates an isolated virtualenv immune to system Python changes
- Use `#!/usr/bin/env python3` shebangs rather than absolute paths (though Homebrew rewrites these anyway)
- The launchd plist generation should resolve paths at generation time and include a `fnsvr doctor` command that validates the plist still points to a working binary
- Document that `brew upgrade` may require `fnsvr schedule --reinstall` to update plist paths

**Detection:** `fnsvr` commands fail with "bad interpreter" or "No such file or directory." launchd jobs show exit code 126 or 127.

**Phase relevance:** Phase covering packaging/Homebrew distribution.

**Confidence:** MEDIUM -- common Homebrew issue, well-documented workaround patterns.

**Sources:**
- [Homebrew: Python for Formula Authors](https://docs.brew.sh/Python-for-Formula-Authors)
- [W3Reference: Fix bad interpreter Error](https://www.w3reference.com/blog/python-virtualenvwrapper-bad-interpreter/)

---

### Pitfall 7: macOS Notifications Silently Swallowed by Focus Mode

**What goes wrong:** macOS Focus Mode (Do Not Disturb) suppresses notifications from osascript. Critical financial email alerts -- the core value of fnsvr -- never reach the user. There is no API to detect whether Focus Mode is active and no way to programmatically bypass it for critical notifications.

**Why it happens:** osascript-generated notifications are treated as low-priority by the Notification Center. Unlike apps with proper notification entitlements (which can be configured to "always deliver" in Focus settings), script-generated notifications cannot be individually allowed through Focus Mode.

**Consequences:** User has Focus Mode enabled during work hours (common for the target persona). K1 deadline notification arrives, gets suppressed. User misses a tax filing deadline.

**Prevention:**
- Document this limitation clearly: "fnsvr notifications respect macOS Focus Mode settings"
- Recommend users add Terminal.app (or whatever app identity osascript uses) to their Focus Mode allow-list
- The weekly digest and `fnsvr stats` serve as secondary safety nets -- notifications are one of three surfaces (notifications, digest, review CLI)
- Consider using `terminal-notifier` (a proper macOS app) instead of raw osascript, as it registers as its own app in Notification Center and can be individually configured in Focus settings
- Long-term: investigate using a proper notification framework via a Swift helper binary

**Detection:** Users report never seeing notifications. `fnsvr stats` shows detections exist but `notified=1` in the database (the notification was "sent" but never displayed).

**Phase relevance:** Phase covering notifier.py. Consider `terminal-notifier` from the start rather than raw osascript.

**Confidence:** MEDIUM -- Focus Mode behavior is documented, but the exact interaction with osascript-generated notifications vs. app notifications needs testing.

**Sources:**
- [FileMinutes: Everything You Need to Know About macOS Focus Mode](https://www.fileminutes.com/blog/everything-you-need-to-know-about-macos-focus-mode-2025/)
- [Apple Support: Turn a Focus on or off on Mac](https://support.apple.com/guide/mac-help/turn-a-focus-on-or-off-mchl999b7c1a/mac)

---

### Pitfall 8: OAuth Token Refresh Fails Silently -- Scan Appears Successful With Zero Results

**What goes wrong:** When a refresh token is revoked (user changed password, manually revoked access, or hit the 50-token limit per client/user), the `google-auth-oauthlib` library raises an exception during token refresh. If the scanner catches this too broadly (e.g., `except Exception`) and continues, the account scan completes with 0 emails scanned and 0 detected -- which looks identical to "no new financial emails found."

**Why it happens:** Defensive error handling (skip account, continue to next) is correct per the tech spec, but without distinguishing "auth failure" from "zero results," the user cannot tell something is wrong.

**Consequences:** An account silently stops being monitored. The user thinks everything is fine because scans complete without errors in the CLI output. Financial emails accumulate undetected.

**Prevention:**
- Auth failures must be surfaced distinctly from zero-result scans. The scan_log should record `status='auth_failed'` separately from `status='completed'`
- `fnsvr stats` should show "last successful scan" per account and flag accounts that haven't had a successful scan in >24 hours
- `fnsvr scan` terminal output should clearly distinguish "0 new emails" from "authentication failed for account X -- run fnsvr setup X"
- Send a macOS notification specifically for auth failures, not just for detections
- A refresh token can also be invalidated if the user's Google password changes. Document this edge case

**Detection:** scan_log shows `emails_scanned=0` for an account that previously had activity. No errors in the errors column if the exception was swallowed.

**Phase relevance:** Phase covering scanner.py. Error handling taxonomy must be designed from the start.

**Confidence:** HIGH -- standard OAuth failure mode, well-documented.

**Sources:**
- [Google OAuth 2 Refresh Token notes](https://hackmd.io/@pclin/BJlq95xgF)
- [Nango: Why is OAuth still hard in 2026](https://nango.dev/blog/why-is-oauth-still-hard)

---

### Pitfall 9: Pattern Matching Misses Due to re.escape() Making Patterns Too Literal

**What goes wrong:** The tech spec says "All patterns are wrapped in `re.escape()`" to ensure literal substring matching. This means a config pattern like `k-1` becomes `k\-1` in the regex, which is fine. But if a user writes a pattern like `1099-*` expecting wildcard behavior (reasonable for YAML config), the `*` gets escaped to `\*` and never matches anything. The pattern silently becomes useless.

**Why it happens:** The tech spec chose re.escape() for safety (avoiding catastrophic backtracking from user-provided regex). But "substring match" and "escaped regex" are different mental models. Users writing YAML config will think in terms of substrings or simple wildcards, not regex.

**Consequences:** Users add custom patterns that silently fail to match. They assume fnsvr is monitoring for those patterns but nothing is being detected. The config-driven extensibility -- a core differentiator -- is undermined by confusing matching semantics.

**Prevention:**
- Use plain Python `in` operator for substring matching instead of regex. It is faster, simpler, and matches the mental model of "does the subject contain this string"
- If regex is needed for power users, use a separate config key (e.g., `subject_regex`) and validate patterns at config load time with a try/except on `re.compile()`
- Add a `fnsvr test-pattern "your pattern" "sample subject line"` command so users can verify their patterns work before waiting for a scan cycle
- Pre-compile and test all patterns during config validation (`fnsvr init` or `fnsvr scan` startup) and warn about patterns that look like they contain regex metacharacters but are being treated as literals

**Detection:** Users report expected emails not being detected despite matching patterns in config. `fnsvr scan --verbose` shows pattern compilation but no matches.

**Phase relevance:** Phase covering detector.py. The matching strategy must be decided before patterns are implemented.

**Confidence:** HIGH -- direct analysis of the tech spec's design choice and its user-facing implications.

---

## Minor Pitfalls

### Pitfall 10: Gmail API Pagination -- Missing Emails Beyond First Page

**What goes wrong:** `messages.list()` returns paginated results with a `nextPageToken`. If the scanner only fetches the first page (up to `maxResults`), emails beyond that page are silently missed. With a 90-day initial lookback across active accounts, 100 results per page may not be enough.

**Prevention:**
- Always follow `nextPageToken` until exhausted, or until a reasonable safety limit (e.g., 1000 messages)
- Log the total number of messages the API reports vs. how many were actually fetched
- The `max_results_per_scan` config should be documented as "per page," not "total cap," or renamed to clarify

**Phase relevance:** Phase covering scanner.py.

**Confidence:** HIGH -- standard API pagination behavior.

---

### Pitfall 11: Attachment Filename Collisions Across Emails

**What goes wrong:** Multiple financial institutions send attachments named `statement.pdf`. The tech spec handles same-email collisions (counter suffix) but if two different emails from different senders both have `statement.pdf`, and the directory structure is only `<account_name>/`, they collide.

**Prevention:**
- Include the email message_id or a date prefix in the directory structure: `<account_name>/<YYYY-MM-DD>_<sanitized_subject>/statement.pdf`
- Or prepend a hash/counter to every downloaded filename: `001_statement.pdf`
- The current "counter suffix" approach handles this but generates unhelpful names like `statement_3.pdf` with no context about which email it came from

**Phase relevance:** Phase covering downloader.py.

**Confidence:** HIGH -- inevitable with financial institution email patterns.

---

### Pitfall 12: Config YAML Parsing -- Tabs vs. Spaces, Encoding Issues

**What goes wrong:** YAML is whitespace-sensitive. Users editing config.yaml in basic text editors may introduce tabs (YAML requires spaces), leading to cryptic parse errors. Special characters in pattern strings (e.g., ampersands, colons) may need quoting.

**Prevention:**
- `fnsvr init` should generate a config with comments explaining YAML formatting rules
- Config validation should catch common YAML errors and provide human-readable messages, not raw PyYAML tracebacks
- Provide a `fnsvr config validate` command that checks config syntax and reports issues before the user waits for a scan cycle to discover problems

**Phase relevance:** Phase covering config.py.

**Confidence:** HIGH -- universal YAML usability issue.

---

### Pitfall 13: SQLite Database Locked During Concurrent Access From Multiple Commands

**What goes wrong:** User runs `fnsvr stats` or `fnsvr review` while a background launchd scan is writing to the database. Without WAL mode (see Pitfall 5), this causes "database is locked" errors. Even with WAL mode, long-running write transactions can still cause issues if the connection timeout is too short.

**Prevention:**
- Ensure WAL mode is active (see Pitfall 5)
- Set `sqlite3.connect(timeout=10)` or higher to allow readers to wait for the writer
- Keep write transactions short -- commit after each email insertion rather than batching an entire account scan in one transaction
- Use `BEGIN IMMEDIATE` for write transactions to fail fast rather than deadlock

**Phase relevance:** Phase covering storage.py.

**Confidence:** HIGH -- standard SQLite concurrency pattern.

**Sources:**
- [SkyPilot Blog: Abusing SQLite to Handle Concurrency](https://blog.skypilot.co/abusing-sqlite-to-handle-concurrency/)
- [SQLite WAL documentation](https://www.sqlite.org/wal.html)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| OAuth / Scanner (Phase 1) | Token expiry after 7 days (Pitfall 1), credential distribution (Pitfall 3) | Decide on embedded vs. user-provided credentials before writing any OAuth code. Set GCP project to Production |
| Scanner / Gmail API | Date filter timezone issues (Pitfall 4), pagination gaps (Pitfall 10) | Use epoch timestamps in queries. Always paginate fully |
| Scanner error handling | Silent auth failures (Pitfall 8) | Distinct error states in scan_log. Surface auth failures prominently |
| Storage / SQLite | WAL mode activation order (Pitfall 5), concurrent access (Pitfall 13) | Set WAL as first pragma. Use connection timeout. Short transactions |
| Detector / Patterns | re.escape() vs. user expectations (Pitfall 9) | Use plain substring matching. Add pattern testing CLI command |
| Notifications | Focus Mode suppression (Pitfall 7) | Consider terminal-notifier. Document limitation. Digest as safety net |
| launchd integration | PATH resolution (Pitfall 2) | Generate plists dynamically with absolute paths. Never use tilde |
| Homebrew packaging | Python upgrade breakage (Pitfall 6) | Use virtualenv_install_with_resources in formula. Add doctor command |
| Config | YAML syntax errors (Pitfall 12) | Validate command. Human-readable error messages |
| Attachments | Filename collisions (Pitfall 11) | Date/subject prefix in directory structure |

## Sources

- [Google: Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Google: Gmail API Usage Limits](https://developers.google.com/workspace/gmail/api/reference/quota)
- [Google: Search and filter messages](https://developers.google.com/workspace/gmail/api/guides/filtering)
- [SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [Homebrew: Python for Formula Authors](https://docs.brew.sh/Python-for-Formula-Authors)
- [launchd.info Tutorial](https://launchd.info/)
- [regular-expressions.info: Catastrophic Backtracking](https://www.regular-expressions.info/catastrophic.html)
- [Simon Willison: Google OAuth for a CLI application](https://til.simonwillison.net/googlecloud/google-oauth-cli-application)
