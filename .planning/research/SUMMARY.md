# Project Research Summary

**Project:** fnsvr -- Local-first Gmail financial email monitor
**Domain:** CLI tool / email monitoring / personal finance automation (macOS)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

fnsvr is a local-first CLI tool that monitors multiple Gmail accounts for financial emails (K1s, 1099s, DocuSign requests, equity grants, wire confirmations) and surfaces them via macOS notifications, markdown digests, and an interactive review workflow. The expert approach for this type of tool is a pipeline architecture with SQLite as the integration database: modules are functions that read config and read/write SQLite, the CLI is the only orchestrator, and the detection engine is kept pure (no I/O). The tech stack is Python 3.11+, Click, raw sqlite3, PyYAML, and the Google API Python client -- all well-validated choices with no exotic dependencies.

The recommended build approach is dependency-driven: foundation modules first (config, storage, detector), then Gmail integration (scanner, downloader), then user-facing output (notifications, digest, review), and finally distribution (launchd, Homebrew, landing page). The detection loop is the critical path -- if pattern matching produces false positives or scanning breaks on token refresh, nothing else matters. Every other module consumes stored detections, so the database schema and scan pipeline must be solid before building outward.

The two highest risks are both OAuth-related and must be resolved before writing any authentication code. First, the credential distribution model: requiring users to create their own GCP project will kill adoption for the target persona (busy founders, not daily developers). The recommendation is to embed client credentials in the package, which is standard practice for desktop OAuth apps per RFC 8252. Second, GCP projects left in "Testing" mode cause tokens to expire after 7 days, silently breaking all scans. The project must be set to "Production" publishing status. Beyond OAuth, the key risks are launchd PATH resolution (plists must use absolute paths, generated dynamically) and pattern matching semantics (use plain substring matching, not re.escape(), to match user mental models).

## Key Findings

### Recommended Stack

The spec's technology choices are well-validated. No stack changes needed -- only minor version bumps for dev dependencies (pytest >=8.0, ruff >=0.6.0). The stack is deliberately minimal: no ORM, no async, no Rich, no Docker. This is correct for a local-first tool targeting 3-5 Gmail accounts on a 4-hour scan interval.

**Core technologies:**
- **Python 3.11+**: Runtime floor -- gets ExceptionGroup, tomllib, match statements, performance gains. 3.14 is current but 3.11 keeps Homebrew compatibility
- **Click 8.1+**: CLI framework -- explicit decorators over Typer's magic; composable for 10+ commands
- **sqlite3 (stdlib)**: Local database -- WAL mode, 3 tables, raw SQL. No ORM justified at this scale
- **google-api-python-client 2.100+**: Gmail API -- cached discovery docs, weekly releases, synchronous (correct for this use case)
- **google-auth-oauthlib 1.1+**: OAuth browser flow -- InstalledAppFlow.run_local_server() for "like gcloud" UX
- **PyYAML 6.0+**: Config parsing -- YAML handles nested pattern lists naturally; TOML would be awkward here
- **launchd (system)**: Scheduling -- the only proper macOS scheduler; cron is deprecated on macOS
- **osascript (system)**: Notifications -- zero-dependency native macOS alerts (consider terminal-notifier for Focus Mode handling)

**Distribution path:** PyPI + pipx first (fastest), then Homebrew tap formula, then aspirational homebrew-core.

### Expected Features

**Must have (table stakes):**
- Multi-account Gmail scanning with per-account error isolation
- Pattern-based financial email detection across 5 categories (tax, signatures, equity, brokerage, banking)
- Config-driven YAML patterns with comprehensive defaults (~70 patterns shipping)
- Scheduled background scanning via launchd (4h scan, weekly digest)
- macOS native notifications with priority-based sounds
- Attachment auto-download (PDF, spreadsheet) organized by account
- Local SQLite storage with audit trail (matched_pattern column)
- Interactive review workflow (y/n/q/a with optional notes)
- Weekly markdown digest grouped by category
- Quick terminal stats command (read-only, no API calls)
- Guided setup (fnsvr init + fnsvr setup) with browser OAuth
- Read-only Gmail scope (gmail.readonly) -- trust decision, not limitation
- Deduplication via UNIQUE(message_id, account_email)
- Error resilience -- one failed account does not block others

**Should have (differentiators):**
- Five-category financial detection taxonomy with priority tiers (critical vs. high)
- Obsidian vault sync for digests (off by default, one config line to enable)
- 90-day initial deep scan ("first run magic moment")
- Cross-account unified view for stats/digest/review
- launchd auto-configuration (no manual plist editing)
- Matched-pattern audit trail for forensic transparency
- Single-file landing page (fnsvr.com) -- trust signal, no tracking

**Defer (v2+):**
- Rich/Textual terminal output (start with Click's built-in formatting)
- Linux/systemd support (architecture isolates platform code)
- Outlook/Microsoft Graph API
- Keychain integration for token storage
- Incremental scanning via Gmail historyId
- Community pattern libraries

### Architecture Approach

Pipeline architecture with SQLite as integration database. Modules do not import each other -- they share data through the database. Only cli.py and scanner.py import multiple internal modules. detector.py is pure (zero I/O, zero side effects). The build order follows a strict dependency graph: Layer 0 (config, storage, detector -- no internal deps), Layer 1 (notifier, downloader, digest, reviewer -- depend on Layer 0), Layer 2 (scanner -- orchestrates Layers 0+1), Layer 3 (cli -- wires everything).

**Major components:**
1. **config.py** -- Load YAML, validate, resolve paths. Foundation for everything else
2. **storage.py** -- SQLite schema init, all CRUD, query helpers. The shared data contract
3. **detector.py** -- Pure pattern matching engine. Zero I/O, highest-value test target
4. **scanner.py** -- Gmail auth, message fetching, scan orchestration. The only compound module
5. **downloader.py** -- Attachment fetch and save. Receives Gmail service object, does not handle auth
6. **notifier.py** -- macOS notifications. Fire-and-forget, never raises
7. **digest.py** -- Read DB, generate markdown. Optionally copy to Obsidian vault
8. **reviewer.py** -- Interactive terminal review loop with y/n/q/a prompts
9. **cli.py** -- Click command definitions, wires all modules together

**Key patterns:** Config-as-dependency-injection (pass config dict, never read files internally). Connection-passing (cli.py creates connection, passes down). Fail-forward scanning (errors collected, never raised mid-loop). Pure detection, impure orchestration.

### Critical Pitfalls

1. **OAuth token expiry after 7 days (Pitfalls 1+3)** -- GCP projects in "Testing" mode kill tokens weekly. Combine with credential distribution: embed client credentials in the package (standard for desktop apps per RFC 8252) and set project to "Production." This is THE most important architectural decision -- must be resolved before writing any OAuth code.

2. **launchd PATH resolution (Pitfall 2)** -- launchd runs without user's shell PATH. Generate plists dynamically with absolute paths via shutil.which() or sys.executable. Never use tilde. Always set StandardOutPath/StandardErrorPath for debugging.

3. **Silent auth failures look like zero results (Pitfall 8)** -- Distinguish auth_failed from completed in scan_log. Surface auth failures in stats, CLI output, and via dedicated notification. An account silently dropping off monitoring is the worst failure mode.

4. **Pattern matching semantics (Pitfall 9)** -- re.escape() confuses users who expect substring or wildcard matching. Use plain Python `in` operator for substring matching. Add a separate `subject_regex` config key for power users. Add `fnsvr test-pattern` command for verification.

5. **Gmail date filter timezone ambiguity (Pitfall 4)** -- Use epoch timestamps in API queries, not date strings. Add 24h buffer to lookback window. Deduplication makes overlapping windows safe.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation + Core Detection

**Rationale:** config.py, storage.py, and detector.py have zero dependencies on each other and zero external API dependencies. They can be built and fully unit-tested locally. This phase also forces the critical credential distribution decision.

**Delivers:** Loadable config, initialized SQLite database with WAL mode, compiled pattern matching engine, comprehensive test suite for detection logic.

**Addresses features:** Config-driven YAML patterns, local SQLite storage, deduplication schema, pattern-based detection across 5 categories.

**Avoids pitfalls:** WAL mode activation order (Pitfall 5), pattern matching semantics (Pitfall 9), YAML parsing errors (Pitfall 12), SQLite concurrent access (Pitfall 13).

### Phase 2: Gmail Integration + Scan Pipeline

**Rationale:** This is where the real integration risk lives. OAuth setup, token management, API pagination, error handling. Must be proven working with real Gmail accounts before building anything that consumes scan results.

**Delivers:** Working `fnsvr init`, `fnsvr setup <account>`, and `fnsvr scan` commands. Emails detected, stored, and deduplicated. Attachments downloaded.

**Addresses features:** Multi-account Gmail scanning, guided setup (init + setup), attachment auto-download, error resilience across accounts, 90-day initial deep scan, read-only Gmail scope.

**Avoids pitfalls:** OAuth token expiry (Pitfall 1), credential distribution (Pitfall 3), date filter timezone (Pitfall 4), silent auth failures (Pitfall 8), pagination gaps (Pitfall 10), filename collisions (Pitfall 11).

### Phase 3: User-Facing Output

**Rationale:** Once scan works and data exists in SQLite, these modules are all relatively independent consumers of stored detections. Low risk, high user value. Can be built in parallel.

**Delivers:** macOS notifications on detection, weekly markdown digest, interactive review workflow, quick stats command. The tool becomes useful day-to-day.

**Addresses features:** macOS native notifications with priority sounds, weekly markdown digest, interactive review workflow, quick terminal stats, cross-account unified view, Obsidian vault sync.

**Avoids pitfalls:** Focus Mode notification suppression (Pitfall 7 -- consider terminal-notifier from the start).

### Phase 4: Automation + Distribution

**Rationale:** The tool works manually. Now make it automatic (launchd) and installable (Homebrew). These are packaging concerns, not feature concerns.

**Delivers:** Background scheduled scanning, automatic digest generation, `brew install` path, `fnsvr doctor` command for health checks.

**Addresses features:** Scheduled background scanning via launchd, launchd auto-configuration, Homebrew formula install.

**Avoids pitfalls:** launchd PATH resolution (Pitfall 2), Homebrew Python upgrade breakage (Pitfall 6).

### Phase 5: Launch + Polish

**Rationale:** Everything works and is installable. Make it discoverable and trustworthy to strangers.

**Delivers:** Landing page (fnsvr.com), PyPI publishing, polished README and CONTRIBUTING docs, comprehensive test suite.

**Addresses features:** Single-file landing page, matched-pattern audit trail documentation.

### Phase Ordering Rationale

- Foundation before integration: config/storage/detector have zero API dependencies and are fully unit-testable. Building them first means Phase 2 starts with proven components.
- Gmail integration before output: Every output module (digest, review, stats, notifications) reads from SQLite. Without scan data, they cannot be meaningfully tested or demonstrated.
- Output before distribution: A tool that works manually but requires `fnsvr scan` is useful. A tool that runs on a schedule but produces no visible output is not. Get the value loop working before automating it.
- Distribution before launch: You cannot launch what you cannot install. Homebrew formula and launchd setup must work before sending people to fnsvr.com.
- OAuth decision gates everything: The embedded-credentials-vs-user-GCP-project decision affects setup flow, documentation, security posture, and the entire Phase 2. Decide in Phase 1, implement in Phase 2.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Gmail Integration):** OAuth token lifecycle edge cases (50-token limit, password change revocation, Google's refresh token rotation policy). Embedded credential distribution implications (rate limits shared across all users of the same client_id). Gmail API pagination behavior with large lookback windows.
- **Phase 4 (Automation + Distribution):** Homebrew formula best practices for Python CLI tools in 2026. launchd plist generation patterns. The `fnsvr doctor` command design.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Config loading, SQLite CRUD, regex matching -- all well-documented, established Python patterns.
- **Phase 3 (User-Facing Output):** Markdown generation, Click prompts, osascript notifications -- straightforward implementations with no unknowns.
- **Phase 5 (Launch):** Static site deployment, PyPI publishing -- well-documented workflows.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies are mature, well-documented, and validated against the spec. No exotic choices. Version pins verified against current PyPI releases. |
| Features | HIGH | Feature landscape thoroughly mapped with competitive analysis. Clear table-stakes vs. differentiator separation. Anti-features well-reasoned. No feature is speculative -- all derive from the target persona's workflow. |
| Architecture | HIGH | Pipeline + SQLite integration DB is a proven pattern for local CLI tools. Module boundaries are clean with explicit dependency graph. Build order follows naturally from dependencies. |
| Pitfalls | HIGH | 13 pitfalls identified with concrete prevention strategies. The critical OAuth pitfalls (1, 3, 8) are well-documented across multiple sources. Pattern matching pitfall (9) is derived from direct spec analysis. |

**Overall confidence:** HIGH

### Gaps to Address

- **Embedded credential rate limits:** If fnsvr embeds a single client_id used by all users, Google may throttle the shared project. Need to verify per-user vs. per-project rate limiting behavior during Phase 2 planning.
- **terminal-notifier vs. osascript:** The Focus Mode pitfall suggests terminal-notifier may be better, but it adds a Homebrew dependency (contradicting the zero-dependency notification goal). Need to test actual Focus Mode behavior with osascript before deciding.
- **Gmail historyId for incremental scanning:** Deferred to v2+ but worth understanding the API surface during Phase 2 in case the 3-day lookback window proves wasteful for power users with many accounts.
- **Google OAuth consent screen verification:** Embedding credentials with "Production" status may trigger Google's verification review process. Need to confirm whether apps with <100 users and gmail.readonly scope are exempt.

## Sources

### Primary (HIGH confidence)
- Google OAuth 2.0 documentation -- token lifecycle, desktop app credentials, consent screen publishing status
- Gmail API documentation -- search operators, pagination, rate limits, scopes
- SQLite WAL documentation -- journal mode, concurrency, Python integration
- Project specs (TECH_SPEC.md, VISION.md, PROJECT.md) -- authoritative product requirements
- Click, PyYAML, google-api-python-client PyPI pages -- version verification

### Secondary (MEDIUM confidence)
- Community reports on OAuth token expiry in Testing mode (HomeSeer Forum, Nango blog)
- Simon Willison's Google OAuth CLI patterns
- launchd.info tutorial and Apple Developer Forums on PATH/environment issues
- Homebrew Python formula author documentation
- macOS Focus Mode notification behavior (FileMinutes)

### Tertiary (LOW confidence)
- Gmail API date filter timezone behavior -- conflicting reports between Google docs and community testing (mitigated by using epoch timestamps regardless)
- Google verification review thresholds for embedded credentials -- needs direct testing

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
