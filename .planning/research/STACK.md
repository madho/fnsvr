# Technology Stack

**Project:** fnsvr -- Local-first Gmail financial email monitor
**Researched:** 2026-03-28

## Recommended Stack

The project spec already makes strong, correct technology choices. This document validates those choices against current ecosystem state, pins specific versions, and flags two areas where the spec should be updated.

### Core Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | >=3.11 | Runtime | Correct floor. 3.11 introduced ExceptionGroup, tomllib, and significant perf gains. 3.14 is current stable but 3.11 minimum keeps compatibility wide enough for Homebrew's system Python while getting all needed features (dataclasses, match statements, type hints). | HIGH |
| Click | >=8.1.0 | CLI framework | Right choice. Click 8.3.x (latest 8.3.1) requires Python >=3.10, so compatible with our 3.11 floor. Battle-tested, composable, excellent for multi-command CLIs. Typer adds unnecessary abstraction for this use case. | HIGH |
| SQLite (stdlib) | sqlite3 | Local database | Correct. stdlib sqlite3 with WAL mode is the right call for local-first. No ORM needed -- the schema is 3 tables. Using raw SQL keeps dependencies minimal and queries transparent. | HIGH |
| PyYAML | >=6.0 | Config parsing | Correct. Latest is 6.0.3. Stable, well-understood. No reason to use alternatives like ruamel.yaml unless round-trip editing is needed (it is not). | HIGH |

### Gmail API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| google-api-python-client | >=2.100.0 | Gmail API access | Correct. Latest is 2.193.0 (releases weekly). The >=2.100.0 floor is fine -- it gets cached discovery documents which is the key reliability feature from v2. | HIGH |
| google-auth-oauthlib | >=1.1.0 | OAuth browser flow | Correct. Latest is 1.3.0. Provides `InstalledAppFlow.run_local_server()` which opens browser for consent -- exactly the "like gcloud auth login" UX the spec calls for. | HIGH |
| google-auth-httplib2 | >=0.1.1 | HTTP transport for google-auth | Correct. Required by google-api-python-client for authorized HTTP. Latest is 0.2.0. | HIGH |

### macOS Platform

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| osascript (system) | N/A | Native notifications | Correct. `osascript -e 'display notification...'` is the simplest path to native macOS notifications without adding a dependency. No reason to use pync or terminal-notifier. | HIGH |
| launchd (system) | N/A | Background scheduling | Correct. launchd is the only proper way to schedule recurring tasks on macOS. Cron exists but is deprecated on macOS and lacks features like RunAtLoad, log management, and proper process lifecycle. | HIGH |

### Development Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | >=0.15.0 | Linting + formatting | Correct. Latest is ~0.15.x (March 2026). Replaces flake8, isort, black in one tool. The pyproject.toml already configures it well (py311 target, line-length 100, E/F/I/N/W/UP rules). | HIGH |
| pytest | >=8.0 | Testing | **Update from spec.** The pyproject.toml pins >=7.0 but pytest 9.0.2 is current. Bump the floor to >=8.0 for improved assertion rewriting and native pyproject.toml support. | MEDIUM |
| pytest-cov | >=4.0 | Coverage | Correct. Latest is in the 7.x range. The >=4.0 floor is fine. | MEDIUM |

### Build System

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| setuptools | >=68.0 | Build backend | **Acceptable but not ideal.** The spec uses setuptools which works fine. For a new pure-Python project in 2026, hatchling or uv_build are more modern choices with less boilerplate. However, setuptools is battle-tested, the pyproject.toml is already written, and switching build backends provides zero user-facing value. Keep setuptools. | MEDIUM |

## Version Pin Updates for pyproject.toml

The existing pyproject.toml is well-written. Two minor updates recommended:

```toml
# Current (fine, keep these)
dependencies = [
    "google-api-python-client>=2.100.0",
    "google-auth-httplib2>=0.1.1",
    "google-auth-oauthlib>=1.1.0",
    "PyYAML>=6.0",
    "click>=8.1.0",
]

# Update dev dependencies
[project.optional-dependencies]
dev = [
    "pytest>=8.0",        # was >=7.0, bump for current ecosystem
    "pytest-cov>=4.0",    # keep as-is
    "ruff>=0.6.0",        # was >=0.4.0, bump for 2026 style guide support
]
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI framework | Click | Typer | Typer wraps Click and adds type-annotation magic. For a tool with this many subcommands and flags, Click's explicit decorators are clearer and have no hidden behavior. Typer's auto-generation is a leaky abstraction when you need precise control over help text and argument parsing. |
| CLI framework | Click | argparse | argparse is stdlib but verbose for multi-command CLIs. Click's decorator pattern is significantly more readable for 10+ commands. |
| Config format | PyYAML | TOML (tomllib) | YAML supports nested lists-of-dicts naturally (the categories config). TOML's array-of-tables syntax would be awkward for pattern lists. YAML is the right call for this config shape. |
| Database | sqlite3 (raw) | SQLAlchemy | 3 tables, 5 queries. An ORM adds 10MB+ of dependency for zero benefit. Raw SQL is more readable at this scale and makes WAL/pragma control explicit. |
| Database | sqlite3 (raw) | DuckDB | DuckDB is for analytics workloads. This is transactional CRUD on small datasets. SQLite is the correct choice. |
| Notifications | osascript | terminal-notifier | terminal-notifier requires a separate install (`brew install terminal-notifier`). osascript is built into macOS. One fewer dependency for the user to manage. |
| Notifications | osascript | pync | pync is a Python wrapper around terminal-notifier, so same problem plus an extra Python dependency. |
| Build backend | setuptools | hatchling | Hatchling is more modern but switching provides no user value. The pyproject.toml is already written for setuptools. |
| Build backend | setuptools | uv_build | uv_build is promising but newer and the Homebrew formula story is less proven. Stick with setuptools for distribution compatibility. |
| Scheduling | launchd | cron | cron is effectively deprecated on macOS. launchd supports RunAtLoad, proper logging, StartCalendarInterval, and integrates with macOS power management (won't wake machine unnecessarily). |
| YAML | PyYAML | ruamel.yaml | ruamel.yaml preserves comments on round-trip but fnsvr only reads config, never writes it. PyYAML is simpler and sufficient. |
| Testing | pytest | unittest | pytest is the standard. Better assertions, fixtures, parametrize. No reason to use unittest in 2026. |

## Distribution Strategy

The spec calls for `brew install fnsvr`. Here is the realistic path:

### Phase 1: PyPI + pipx (ship first)
```bash
pip install fnsvr        # Works in any venv
pipx install fnsvr       # Recommended for end users, isolated install
```
This is the fastest path to distribution. Publish to PyPI, tell users to `pipx install fnsvr`.

### Phase 2: Homebrew formula (after PyPI is stable)
```bash
brew tap madho/fnsvr
brew install fnsvr
```
A Homebrew tap formula that wraps `pip install` into a virtualenv. This requires:
1. A stable PyPI release
2. A formula that creates a virtualenv and installs from PyPI
3. Proper `bin/fnsvr` symlink

Homebrew's own docs recommend against Python package formulae in the core repo, but tap formulae work well for this. The formula template is straightforward -- many Python CLI tools use this pattern (e.g., httpie, pgcli, litecli).

### Phase 3: Homebrew core (aspirational)
Getting into homebrew-core requires significant adoption. Not a v0.1 goal.

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| Rich / Textual | The spec calls for simple terminal output. Rich adds visual flair but also 5MB+ of dependency. Click's built-in `echo`, `style`, and `progressbar` are sufficient. If the interactive review UX feels flat after v0.1, Rich is the upgrade path -- but start without it. |
| SQLAlchemy / Peewee | Overkill for 3 tables. Adds dependency weight and abstraction that obscures the simple SQL underneath. |
| asyncio / aiohttp | Gmail API calls are sequential per account. The scan runs every 4 hours unattended. There is no latency-sensitive user waiting. Synchronous code is simpler to debug and the google-api-python-client is synchronous. |
| Docker | This is a local-first macOS tool. Docker adds friction, breaks osascript notifications, and contradicts the "install once, forget it exists" philosophy. |
| Any database besides SQLite | Postgres, MySQL, etc. require a running server. Local-first means a single file database. SQLite is the only correct answer. |
| Celery / APScheduler | launchd handles scheduling. Adding an in-process scheduler means the process must stay running. launchd launches on schedule, the process runs and exits. Simpler, more reliable, better for battery. |
| Keychain for token storage | The spec stores OAuth tokens as JSON files with 600 permissions. macOS Keychain integration (via `keyring` library) is more secure but adds complexity for v0.1. File-based tokens with restrictive permissions match what gcloud and gh CLI do. Revisit for v0.2 if users request it. |

## Installation

```bash
# Development setup
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest
ruff check src/ tests/
ruff format src/ tests/

# User installation (after PyPI publish)
pipx install fnsvr
fnsvr init
fnsvr setup personal
```

## Sources

- [google-api-python-client on PyPI](https://pypi.org/project/google-api-python-client/) -- v2.193.0, weekly releases
- [Click on PyPI](https://pypi.org/project/click/) -- v8.3.1, requires Python >=3.10
- [PyYAML on PyPI](https://pypi.org/project/PyYAML/) -- v6.0.3
- [google-auth-oauthlib on PyPI](https://pypi.org/project/google-auth-oauthlib/) -- v1.3.0
- [Ruff releases](https://github.com/astral-sh/ruff/releases) -- v0.15.x as of March 2026
- [pytest on PyPI](https://pypi.org/project/pytest/) -- v9.0.2
- [Python versions status](https://devguide.python.org/versions/) -- 3.14 is current feature release, 3.11+ all supported
- [Homebrew Python documentation](https://docs.brew.sh/Python-for-Formula-Authors) -- formula guidance for Python packages
- [Python packaging best practices 2026](https://dasroot.net/posts/2026/01/python-packaging-best-practices-setuptools-poetry-hatch/) -- build backend comparison
