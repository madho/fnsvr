# CLAUDE.md

## What is fnsvr?

fnsvr (pronounced "fin-sever") is a local-first CLI tool that scans multiple Gmail accounts for financial emails you can't afford to miss -- K1s, 1099s, investment statements, bank wires, equity grants, and signature requests. It runs on macOS via launchd, stores everything in local SQLite, sends native notifications, and generates markdown digests that optionally sync to Obsidian.

## Repository

- GitHub: https://github.com/madho/fnsvr.git
- License: MIT
- Local dev path: /Users/madho/Desktop/cc/fnsvr

## Start Here

Read these documents BEFORE writing any code. They define what to build and how:

1. **`docs/VISION.md`** -- Why this exists, who it's for, design principles
2. **`docs/PRD.md`** -- Product requirements, user stories, acceptance criteria
3. **`docs/TECH_SPEC.md`** -- Architecture, module contracts, data model, config schema

The `config.example.yaml` is the reference config that ships with the project. All detection patterns live there.

## Tech Stack

- Python 3.11+, type hints throughout
- Gmail API (google-api-python-client) -- READ-ONLY access only (gmail.readonly scope)
- SQLite via stdlib sqlite3 (WAL mode, no ORM)
- Click for CLI
- PyYAML for config
- pytest for tests
- macOS osascript for native notifications
- launchd for scheduling

## Target Project Structure

```
fnsvr/
  src/fnsvr/
    __init__.py          # Version
    cli.py               # Click CLI entry point
    config.py            # Config loading, validation, path resolution
    detector.py          # Pattern matching engine (pure functions)
    scanner.py           # Gmail API connection and scanning
    downloader.py        # Attachment downloading
    storage.py           # SQLite database layer
    notifier.py          # macOS notifications via osascript
    digest.py            # Markdown digest generator
    reviewer.py          # Interactive review CLI
  config.example.yaml    # Template config
  launchd/
    com.fnsvr.scan.plist
    com.fnsvr.digest.plist
  tests/
    test_detector.py
    test_storage.py
    test_digest.py
    test_config.py
  docs/
    VISION.md
    PRD.md
    TECH_SPEC.md
  pyproject.toml
  README.md
  CONTRIBUTING.md
  LICENSE
  CLAUDE.md
  .gitignore
```

## CLI Commands (target)

```bash
fnsvr init                        # Create ~/.fnsvr/ and copy example config
fnsvr setup <account_name>        # OAuth flow for a Gmail account
fnsvr scan                        # Regular scan (last 3 days)
fnsvr scan --initial              # First run (90-day lookback)
fnsvr scan --days 14              # Custom lookback
fnsvr scan --account personal     # Single account
fnsvr digest                      # Last 7 days
fnsvr digest --days 30
fnsvr digest --unreviewed
fnsvr stats                       # Quick terminal stats
fnsvr review                      # Interactive review
fnsvr review --category tax_documents
fnsvr review --mark-all
```

## Key Design Constraints

1. **Local-first.** Zero cloud dependencies. All data stays on the user's machine.
2. **Read-only Gmail.** Only gmail.readonly scope. The app CANNOT modify, delete, or send emails.
3. **Config-driven patterns.** All detection patterns live in config.yaml. Adding a new sender or keyword should never require a code change.
4. **No ORM.** Raw SQL via sqlite3.
5. **macOS-first.** Notifications use osascript. Scheduling uses launchd. Core logic should be cross-platform.
6. **Minimal dependencies.** Only google-api-python-client, google-auth-oauthlib, click, pyyaml.

## Code Style

- Type hints on all function signatures
- Docstrings on all public functions and modules
- No em-dashes in any text output or documentation
- ruff for linting/formatting (target-version py311, line-length 100)
- Tests for all pure logic (detector, storage, digest, config validation)

## Build Order (suggested)

1. `config.py` + validate against `config.example.yaml`
2. `storage.py` -- SQLite schema and CRUD
3. `detector.py` -- pattern compilation and matching (pure, testable)
4. `scanner.py` -- Gmail API auth and scanning
5. `downloader.py` -- attachment downloading
6. `notifier.py` -- macOS notifications
7. `digest.py` -- markdown digest generation
8. `reviewer.py` -- interactive review
9. `cli.py` -- Click commands wiring it all together
10. Tests for each module
11. README.md, CONTRIBUTING.md
12. launchd plists

## Development Commands

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pytest
pytest -v
ruff check src/ tests/
ruff format src/ tests/
```
