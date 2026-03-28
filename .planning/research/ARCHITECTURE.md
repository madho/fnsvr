# Architecture Patterns

**Domain:** Local-first email monitoring CLI tool (macOS)
**Project:** fnsvr
**Researched:** 2026-03-28

## Recommended Architecture

fnsvr follows a **pipeline architecture** with SQLite as the integration database. This is the correct pattern for a local-first CLI tool: no event bus, no message queue, no shared mutable state. Modules are functions that read config and read/write SQLite. The CLI layer is the only orchestrator.

```
USER COMMANDS                     SCHEDULED (launchd)
     |                                  |
     v                                  v
  cli.py  <-- Click entry point, wires everything together
     |
     +-- config.py  (load + validate YAML, resolve paths)
     |
     +-- scanner.py (Gmail API auth + message fetching)
     |       |
     |       +-- detector.py (pure pattern matching, no I/O)
     |       |
     |       +-- downloader.py (attachment fetch + save)
     |       |
     |       +-- notifier.py (macOS osascript, fire-and-forget)
     |
     +-- storage.py (SQLite CRUD, shared by all modules below)
     |
     +-- digest.py (read DB -> markdown file)
     |
     +-- reviewer.py (read DB -> interactive TUI -> write DB)
```

### Key Architectural Decisions

**SQLite as the integration point, not function calls.** Modules do not import each other (except cli.py importing all of them and scanner.py calling detector/downloader/notifier). The database is the shared state. This means:
- `digest.py` never imports `scanner.py` -- it queries `detected_emails`
- `reviewer.py` never imports `detector.py` -- it queries the same table
- `stats` command is just SQL queries against the DB

**Scanner is the only compound module.** `scanner.py` orchestrates a single scan run: authenticate, fetch messages, run detector, trigger downloads, fire notifications, log results. Every other module is a leaf node that either reads or writes to SQLite independently.

**detector.py is a pure function module.** Zero side effects, zero I/O. Takes strings in, returns dataclasses out. This is the most testable and most important module to get right -- every false negative is a missed K1.

## Component Boundaries

| Component | Responsibility | Reads From | Writes To | Imports |
|-----------|---------------|------------|-----------|---------|
| `config.py` | Load YAML, validate, resolve paths | Filesystem (config.yaml) | Filesystem (create dirs) | PyYAML, pathlib |
| `detector.py` | Compile regex, match email fields | Nothing (pure input) | Nothing (pure output) | re, dataclasses |
| `storage.py` | Schema init, all CRUD, query helpers | SQLite | SQLite | sqlite3 |
| `scanner.py` | Gmail auth, fetch, orchestrate scan | Gmail API, config dict | SQLite (via storage), filesystem (via downloader) | google-api-python-client, detector, downloader, notifier, storage |
| `downloader.py` | Fetch attachments, save to disk | Gmail API (attachment data) | Filesystem, SQLite (via storage) | base64, pathlib |
| `notifier.py` | Send macOS notifications | Nothing | osascript subprocess | subprocess, platform |
| `digest.py` | Generate markdown from DB data | SQLite (via storage) | Filesystem (markdown files) | pathlib |
| `reviewer.py` | Interactive review loop | SQLite (via storage), stdin | SQLite (via storage) | click (for prompts) |
| `cli.py` | Command definitions, wiring | All modules | stdout, delegates to modules | click, all other modules |

### Boundary Rules

1. **Only `cli.py` and `scanner.py` may import multiple internal modules.** Every other module should be independently testable.
2. **`detector.py` imports nothing from fnsvr.** It is a pure library.
3. **`notifier.py` never raises.** Notification failure must not halt a scan. Wrap all osascript calls in try/except with logging.
4. **`storage.py` owns the connection.** Other modules receive a `sqlite3.Connection` object; they do not create their own connections.
5. **`downloader.py` receives a Gmail API service object.** It does not handle auth.

## Data Flow

### Flow 1: Scan (the critical path)

```
fnsvr scan
    |
    v
cli.py: load_config() -> config dict
    |
    v
cli.py: storage.init_db(config) -> sqlite3.Connection
    |
    v
cli.py: detector.compile_patterns(config["categories"]) -> [CompiledCategory]
    |
    v
FOR EACH account in config["accounts"]:
    |
    v
    scanner.scan_account(account, config, conn, patterns, lookback, config_dir)
        |
        +-- get_gmail_service(account, config_dir) -> service | None
        |       (if None: log error, skip account, continue)
        |
        +-- storage.log_scan_start(conn, account) -> scan_log_id
        |
        +-- service.messages().list(...) -> [message_ids]
        |
        +-- FOR EACH message_id:
        |       |
        |       +-- service.messages().get(...) -> message_data
        |       |
        |       +-- extract subject, sender, date from headers
        |       |
        |       +-- detector.match_email(subject, sender, patterns) -> DetectionMatch | None
        |       |
        |       +-- IF match:
        |       |       |
        |       |       +-- storage.insert_email(conn, ...) -> email_id | None (dedup)
        |       |       |
        |       |       +-- IF email_id (new, not duplicate):
        |       |               |
        |       |               +-- downloader.process_attachments(service, conn, email_id, ...)
        |       |               |
        |       |               +-- notifier.notify(title, message, ...)
        |       |
        |       +-- IF no match: skip (no logging of non-matches)
        |
        +-- storage.log_scan_complete(conn, scan_log_id, stats)
    |
    v
cli.py: print summary to stdout
```

**Critical insight:** The deduplication check (`UNIQUE(message_id, account_email)`) happens at the storage layer, not the scanner. This means scanner always attempts to insert and gracefully handles the duplicate. This is correct -- it avoids a separate SELECT-before-INSERT race and keeps detector/scanner simple.

### Flow 2: Digest

```
fnsvr digest --days 7
    |
    v
cli.py: load_config(), init_db()
    |
    v
storage.get_emails_since(conn, days=7) -> [email dicts]
    |
    v
digest.generate_digest(emails, title) -> markdown string
    |
    v
digest.save_digest(markdown, config) -> Path
    |                                      |
    v                                      +-- IF obsidian_copy: copy to vault
notifier.notify_digest_ready(path, count)
```

### Flow 3: Review

```
fnsvr review
    |
    v
cli.py: load_config(), init_db()
    |
    v
storage.get_unreviewed(conn, category=None) -> [email dicts]
    |
    v
reviewer.review_interactive(conn, emails) -> reviewed_count
    |
    FOR EACH email:
        display details -> prompt [y/n/q/a] -> IF y: storage.mark_reviewed(conn, id, notes)
```

### Flow 4: Stats

```
fnsvr stats
    |
    v
cli.py: load_config(), init_db()
    |
    v
storage.get_stats(conn) -> dict of counts
    |
    v
cli.py: format and print to stdout
```

## Patterns to Follow

### Pattern 1: Config-as-dependency-injection

Every module function receives what it needs as arguments. No module reaches into global state or reads config.yaml itself.

```python
# GOOD: config passed in
def scan_account(account: dict, config: dict, conn: Connection, ...):

# BAD: module reads config internally
def scan_account(account_name: str):
    config = load_config()  # hidden dependency
```

**Why:** Testability. You can pass a test config dict without touching the filesystem.

### Pattern 2: Connection-passing (not connection-creating)

```python
# GOOD: cli.py creates connection, passes it down
conn = storage.init_db(config)
scanner.scan_account(..., conn=conn, ...)
digest_emails = storage.get_emails_since(conn, days=7)

# BAD: each module opens its own connection
def scan_account(...):
    conn = sqlite3.connect(db_path)  # hidden, uncontrolled
```

**Why:** WAL mode enables concurrent reads, but connection lifecycle should be explicit and controlled by the CLI layer.

### Pattern 3: Fail-forward scanning

```python
# In scanner.py
for msg_id in message_ids:
    try:
        # fetch, detect, download, notify
    except Exception as e:
        errors.append(f"Message {msg_id}: {e}")
        continue  # never halt the loop

# After loop: log all errors to scan_log
```

**Why:** A single malformed email must not prevent scanning the other 99. Errors are collected, not raised.

### Pattern 4: Pure detection, impure orchestration

```python
# detector.py -- PURE (no I/O, no DB, no network)
def match_email(subject: str, sender: str, patterns: list) -> DetectionMatch | None:
    ...

# scanner.py -- IMPURE (orchestrates I/O around pure detection)
match = detector.match_email(subject, sender, patterns)
if match:
    storage.insert_email(conn, ...)
```

**Why:** The detection logic is the core business logic. Keeping it pure means it can be tested with just strings and assertions, no mocking required.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Module-to-module imports (spaghetti)

**What:** digest.py importing scanner.py to "get fresh data"
**Why bad:** Creates circular dependencies, makes modules untestable in isolation
**Instead:** Both read from SQLite. The database is the contract.

### Anti-Pattern 2: ORM or abstraction layer over SQLite

**What:** Adding SQLAlchemy, Peewee, or a custom model layer
**Why bad:** For a single-user local tool with 3 tables, an ORM adds complexity with zero benefit. Raw SQL is readable, debuggable, and the schema is stable.
**Instead:** Raw SQL in storage.py with well-named helper functions.

### Anti-Pattern 3: Async/await for Gmail API calls

**What:** Using aiohttp or asyncio for Gmail fetching
**Why bad:** The Gmail API Python client is synchronous. Wrapping it in async adds complexity without throughput benefit for a background process scanning 3-5 accounts sequentially. The tool runs every 4 hours -- shaving 2 seconds off a 30-second scan is irrelevant.
**Instead:** Synchronous, sequential, simple.

### Anti-Pattern 4: Plugin architecture for detection

**What:** Making detector.py a plugin system where users can write Python detection scripts
**Why bad:** The target user is "technically comfortable but not writing code daily." YAML patterns are the right abstraction level. A plugin system adds attack surface, debugging complexity, and maintenance burden.
**Instead:** YAML-driven patterns with regex matching. If a user needs more, they can modify the source.

### Anti-Pattern 5: Shared state or singleton patterns

**What:** Global database connection, module-level config cache
**Why bad:** Makes testing require careful setup/teardown, creates hidden dependencies
**Instead:** Pass connection and config explicitly to every function.

## Build Order (Dependency-Driven)

The build order follows a strict dependency graph. Each module should be buildable and testable before its dependents.

```
Layer 0 (no internal deps):   config.py, detector.py, storage.py
Layer 1 (depends on Layer 0): notifier.py, downloader.py, digest.py, reviewer.py
Layer 2 (depends on Layers 0+1): scanner.py
Layer 3 (depends on everything): cli.py
```

### Recommended sequence with rationale:

| Order | Module | Rationale | Can Test? |
|-------|--------|-----------|-----------|
| 1 | `config.py` | Everything else needs config. Build and test config loading/validation first. | Yes, filesystem only |
| 2 | `storage.py` | Second foundation. Define schema, write CRUD helpers, test with in-memory SQLite. | Yes, in-memory DB |
| 3 | `detector.py` | Pure logic, zero deps. Build pattern engine, write comprehensive tests. This is the highest-value test target. | Yes, pure functions |
| 4 | `scanner.py` (auth only) | Get OAuth flow working with a real Gmail account. This is the integration risk -- if auth doesn't work, nothing works. | Manual test only |
| 5 | `scanner.py` (full scan) | Wire detector + storage into the scan loop. Test with a real account. | Manual + unit tests for helpers |
| 6 | `downloader.py` | Attachment fetching. Depends on a working scanner to get message IDs. | Manual test |
| 7 | `notifier.py` | Simple osascript wrapper. Low risk, low dependency. Can be built anytime after config. | Manual test (macOS only) |
| 8 | `digest.py` | Reads from DB (needs storage), writes markdown. Straightforward once storage has data. | Yes, with test DB |
| 9 | `reviewer.py` | Interactive TUI. Needs storage with data. Build last among data modules. | Semi-manual (stdin) |
| 10 | `cli.py` | Wire everything together with Click commands. | Integration tests |
| 11 | Tests | Formalize manual tests into pytest suite. detector and storage are highest priority. | -- |
| 12 | launchd plists | Scheduling config. Needs working CLI. | Manual test |

### Phase grouping implications for roadmap:

**Phase 1 -- Foundation (config + storage + detector):** These three modules have zero external dependencies on each other and can be built and fully unit-tested without Gmail API access. This is the "can I build this locally in an afternoon" phase.

**Phase 2 -- Gmail Integration (scanner + downloader):** This is where the real integration risk lives. OAuth setup, token management, API pagination, error handling. This phase should end with a working `fnsvr scan` that detects and stores emails.

**Phase 3 -- User-Facing Features (notifier + digest + reviewer + cli):** Once scan works, these are all relatively independent output modules. They read from the DB and present data in different formats. Low risk, high user value.

**Phase 4 -- Distribution (launchd + Homebrew + landing page):** Packaging and scheduling. This is "make it installable and automatic."

## Scalability Considerations

| Concern | 1-2 accounts | 5 accounts | 10+ accounts |
|---------|-------------|------------|-------------|
| Scan duration | ~10s | ~30s | ~60s+ |
| SQLite size | <1MB/year | <5MB/year | Consider archiving old scans |
| Attachment storage | ~100MB/year | ~500MB/year | Add config for max storage / auto-cleanup |
| Gmail API quota | Not a concern | Not a concern | May hit rate limits, add exponential backoff |

For the target use case (3-5 accounts, 4-hour scan interval), none of these are real concerns. The architecture handles them naturally:
- WAL mode handles concurrent read/write safely
- Sequential account scanning avoids API rate issues
- SQLite is performant for millions of rows (this tool will have thousands)

## Sources

- Project specs: `Docs/TECH_SPEC.md`, `Docs/CLAUDE.md`, `.planning/PROJECT.md` (HIGH confidence -- authoritative project documents)
- SQLite WAL mode documentation: well-established, no verification needed (HIGH confidence)
- Gmail API Python client behavior (synchronous, quota limits): based on direct experience with the library (HIGH confidence)
- Click CLI framework patterns: standard usage, well-documented (HIGH confidence)
