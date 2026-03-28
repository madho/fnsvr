# Phase 1: Foundation - Research

**Researched:** 2026-03-28
**Domain:** Python infrastructure modules -- config loading, SQLite storage, pattern matching
**Confidence:** HIGH

## Summary

Phase 1 builds three pure infrastructure modules (`config.py`, `storage.py`, `detector.py`) with full unit test coverage. All three are greenfield, have zero external API dependencies, and are defined by precise contracts in TECH_SPEC.md. The tech stack is entirely stdlib Python plus PyYAML -- no Gmail API, no Click CLI, no platform-specific code.

The primary risk in this phase is not technical complexity but contract fidelity: the module signatures and behaviors defined in TECH_SPEC.md are the API that Phase 2+ modules will consume. Getting these wrong means rework. The secondary risk is the detector pattern matching approach -- CONTEXT.md locks the decision to use plain substring matching (case-insensitive `in` operator) rather than regex, which is simpler but means the TECH_SPEC's `re.Pattern` / `re.escape()` / `re.IGNORECASE` types need to be adapted.

**Primary recommendation:** Follow TECH_SPEC.md contracts exactly for function signatures and data types, but replace the regex-based matching in detector.py with plain `str.lower()` + `in` substring matching per the CONTEXT.md decision. Build config -> storage -> detector in order, with tests for each before moving to the next.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None explicitly locked -- all implementation choices at Claude's discretion.

### Claude's Discretion
All implementation choices are at Claude's discretion -- pure infrastructure phase. Follow the TECH_SPEC.md module contracts precisely. Key notes from research:
- Use plain substring matching (case-insensitive `in` operator) rather than re.escape() regex for pattern matching -- simpler, faster, matches config-file users' mental model
- SQLite WAL mode with foreign_keys=ON
- Config validation should fail fast with clear error messages
- detector.py must be pure functions with zero side effects (no I/O, no DB, no filesystem)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | `fnsvr init` creates ~/.fnsvr/ and copies example config | config.py `init_config()` + bundled config.example.yaml via `importlib.resources` or `__file__` relative path |
| CFG-02 | Multiple Gmail accounts in config.yaml with name, email, credentials, token paths | config.py `load_config()` validates accounts list structure |
| CFG-03 | Validates required top-level keys, rejects invalid YAML with clear errors | config.py `load_config()` with explicit key checks, raises ValueError |
| CFG-04 | Path values expand ~ and $ENV_VARS | config.py `resolve_path()` using `os.path.expanduser()` + `os.path.expandvars()` |
| CFG-05 | Config dir overridable via FNSVR_CONFIG_DIR env var | config.py `get_config_dir()` checks `os.environ.get("FNSVR_CONFIG_DIR")` |
| STOR-01 | SQLite initializes with detected_emails, attachments, scan_log tables | storage.py `init_db()` with CREATE TABLE IF NOT EXISTS |
| STOR-02 | WAL journal mode for safe concurrent reads | storage.py sets `PRAGMA journal_mode=WAL` on connection |
| STOR-03 | Tables indexed on account, category, priority, reviewed, date_received | storage.py `init_db()` creates 5 indexes per TECH_SPEC |
| STOR-04 | No email content beyond subject, snippet (500 chars), sender stored | Schema enforcement -- snippet column is TEXT, truncation enforced at insert |
| DET-01 | Match subjects and senders with case-insensitive substring matching | detector.py `match_email()` using `pattern.lower() in subject.lower()` |
| DET-02 | All patterns config-driven in YAML, zero hardcoded | detector.py `compile_patterns()` reads from config dict, no defaults |
| DET-03 | 5 categories: tax_documents, signature_requests, equity_grants, brokerage_statements, bank_statements | Validated against config.example.yaml which defines all 5 |
| DET-04 | Subject patterns checked before sender; first match wins | detector.py `match_email()` iterates subjects first per category, then senders, returns on first hit |
| DET-05 | Detection records: message_id, account, category, priority, subject, sender, date, snippet, matched_pattern, attachment status | DetectionMatch dataclass + storage insert function |
| DET-06 | Duplicate emails not re-detected (message_id + account_email unique) | UNIQUE constraint in schema + IntegrityError catch in insert |
| TEST-01 | Unit tests for detector: pattern compilation, matching, case insensitivity, no-match, priority order | test_detector.py with parametrized tests |
| TEST-02 | Unit tests for storage: DB init, insert, dedup, queries, mark reviewed, stats | test_storage.py with tmp_path fixture for temp databases |
| TEST-03 | Unit tests for config: loading, validation errors, path resolution, missing file | test_config.py with tmp_path for temp config files |
</phase_requirements>

## Standard Stack

### Core (Phase 1 only -- no Gmail API needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.11 | Runtime | Minimum for dataclasses improvements, match statements, tomllib. System has 3.14.3. |
| PyYAML | 6.0.3 | Config parsing | Only external dependency for Phase 1. Stable, latest release. |
| sqlite3 | stdlib | Database | Built-in, WAL mode support, no ORM needed for 3 tables. |
| dataclasses | stdlib | Data types | DetectionMatch, CompiledCategory structs. |
| pathlib | stdlib | Path handling | Path expansion, directory creation. |
| os | stdlib | Env vars | FNSVR_CONFIG_DIR, expandvars. |
| shutil | stdlib | File copy | init_config copies example config. |
| re | stdlib | NOT USED | CONTEXT.md decision: plain substring matching, not regex. Keep import only if needed for future phases. |

### Development
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test runner | All unit tests. Latest stable. |
| pytest-cov | >=4.0 | Coverage | Measure test coverage. |
| ruff | 0.15.8 | Lint + format | Pre-commit quality checks. Latest stable. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain substring matching | re.escape() + re.IGNORECASE | Regex adds complexity with zero benefit for literal substring patterns. CONTEXT.md locks this decision. |
| tmp_path (pytest) | tempfile.mktemp() | TECH_SPEC suggests tempfile.mktemp but tmp_path is pytest's built-in fixture, cleaner, auto-cleaned. Use tmp_path. |
| Raw dict config | Pydantic model | Overkill for validation of 4 top-level keys. Manual validation with clear error messages is simpler and dependency-free. |

**Installation:**
```bash
pip install -e ".[dev]"
```

## Architecture Patterns

### Project Structure (Phase 1 scope)
```
fnsvr/
  src/fnsvr/
    __init__.py          # Version string: __version__ = "0.1.0"
    config.py            # Config loading, validation, path resolution
    storage.py           # SQLite database layer
    detector.py          # Pattern matching engine (pure functions)
  config.example.yaml    # Reference config (shipped with package)
  tests/
    __init__.py          # Empty, makes tests a package
    conftest.py          # Shared fixtures (sample config dict, tmp db)
    test_config.py
    test_storage.py
    test_detector.py
  pyproject.toml
```

### Pattern 1: Config as Validated Dict
**What:** `load_config()` returns a plain dict, not a typed object. Validation happens at load time with fail-fast ValueError.
**When to use:** Config shape is stable, consumed by multiple modules as simple key lookups.
**Example:**
```python
# Source: TECH_SPEC.md section 2.1
def load_config(config_path: Path | None = None) -> dict:
    """Load, validate, return config dict. Raises FileNotFoundError or ValueError."""
    if config_path is None:
        config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError(f"Config must be a YAML mapping, got {type(config).__name__}")

    required_keys = {"accounts", "paths", "categories", "scan"}
    missing = required_keys - config.keys()
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(sorted(missing))}")

    # Validate accounts is non-empty list
    if not config.get("accounts") or not isinstance(config["accounts"], list):
        raise ValueError("'accounts' must be a non-empty list")

    return config
```

### Pattern 2: Pure Detection Functions
**What:** detector.py has zero side effects -- no DB, no filesystem, no network. Takes data in, returns data out.
**When to use:** Core matching logic that must be trivially testable.
**Example:**
```python
# Source: TECH_SPEC.md section 2.2, adapted per CONTEXT.md (substring not regex)
@dataclass
class CompiledCategory:
    key: str
    label: str
    priority: str
    subject_patterns: list[str]  # lowercase strings for substring matching
    sender_patterns: list[str]   # lowercase strings for substring matching

def compile_patterns(categories: dict) -> list[CompiledCategory]:
    """Pre-compile all patterns from config. Called once per scan run."""
    compiled = []
    for key, cat in categories.items():
        compiled.append(CompiledCategory(
            key=key,
            label=cat["label"],
            priority=cat["priority"],
            subject_patterns=[p.lower() for p in cat.get("subject_patterns", [])],
            sender_patterns=[p.lower() for p in cat.get("sender_patterns", [])],
        ))
    return compiled

def match_email(
    subject: str, sender: str, patterns: list[CompiledCategory]
) -> DetectionMatch | None:
    """Test subject then sender patterns. First match wins. Returns None if no match."""
    subject_lower = subject.lower()
    sender_lower = sender.lower()

    for cat in patterns:
        for pattern in cat.subject_patterns:
            if pattern in subject_lower:
                return DetectionMatch(
                    category=cat.key,
                    priority=cat.priority,
                    label=cat.label,
                    matched_pattern=f"subject:{pattern}",
                )
        for pattern in cat.sender_patterns:
            if pattern in sender_lower:
                return DetectionMatch(
                    category=cat.key,
                    priority=cat.priority,
                    label=cat.label,
                    matched_pattern=f"sender:{pattern}",
                )
    return None
```

### Pattern 3: SQLite Connection Factory
**What:** `init_db()` returns a configured `sqlite3.Connection` with WAL mode, foreign keys, and schema created.
**When to use:** Every module that touches the database receives a connection, never creates one.
**Example:**
```python
# Source: TECH_SPEC.md section 2.3
def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize database with schema. Returns configured connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row  # dict-like access

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS detected_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_email TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            subject TEXT,
            sender TEXT,
            date_received TEXT,
            snippet TEXT,
            matched_pattern TEXT,
            has_attachments INTEGER DEFAULT 0,
            notified INTEGER DEFAULT 0,
            reviewed INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(message_id, account_email)
        );
        -- indexes and other tables...
    """)
    conn.commit()
    return conn
```

### Anti-Patterns to Avoid
- **Global DB connection:** Each function should receive `conn` as a parameter. Never use a module-level connection.
- **Hardcoded patterns:** detector.py must never contain pattern strings. All patterns come from the config dict.
- **Catching broad exceptions in config:** Let `yaml.YAMLError` propagate as-is or wrap in `ValueError` with context. Never silently return a default config.
- **Using re.compile when substring suffices:** CONTEXT.md decision is plain `in` matching. Do not import `re` in detector.py.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom config parser | PyYAML `yaml.safe_load()` | Edge cases in YAML spec are endless. safe_load handles anchors, multiline, quoting. |
| Path expansion | Manual string replacement for ~ and $VARS | `os.path.expanduser()` + `os.path.expandvars()` | Handles edge cases (no HOME set, nested vars, Windows paths). |
| SQLite connection pooling | Connection manager class | Pass `sqlite3.Connection` directly | Single-process tool. No connection pool needed. |
| Temp files in tests | Manual mktemp + cleanup | pytest `tmp_path` fixture | Auto-cleanup, unique per test, no test isolation bugs. |
| Config dir creation | Recursive mkdir logic | `Path.mkdir(parents=True, exist_ok=True)` | One line, handles all edge cases. |

**Key insight:** Phase 1 is entirely stdlib Python + PyYAML. Every "complex" problem here has a stdlib solution. Resist adding dependencies.

## Common Pitfalls

### Pitfall 1: yaml.safe_load returns None for empty files
**What goes wrong:** Empty or whitespace-only YAML file returns `None`, not an empty dict. Code that does `config["accounts"]` crashes with `TypeError: 'NoneType' not subscriptable`.
**Why it happens:** `yaml.safe_load("")` returns `None`, not `{}`.
**How to avoid:** Check `if not isinstance(config, dict)` immediately after `safe_load()`.
**Warning signs:** Tests pass with valid config but crash on empty or malformed files.

### Pitfall 2: SQLite WAL pragma must be set before any writes
**What goes wrong:** Setting `PRAGMA journal_mode=WAL` after creating tables may not take effect.
**Why it happens:** SQLite locks the journal mode at first write in some edge cases.
**How to avoid:** Set pragmas immediately after `sqlite3.connect()`, before any CREATE TABLE.
**Warning signs:** `PRAGMA journal_mode` query returns "delete" instead of "wal".

### Pitfall 3: sqlite3.Row requires cursor, not connection.execute
**What goes wrong:** `conn.row_factory = sqlite3.Row` works with `conn.execute()` in modern Python, but some patterns break if you mix cursor and connection execution.
**Why it happens:** `row_factory` is set on the connection and inherited by cursors created from it.
**How to avoid:** Set `conn.row_factory = sqlite3.Row` once after connect. Use `conn.execute()` consistently (Python 3.11+ supports this fine).
**Warning signs:** Some queries return tuples, others return Row objects.

### Pitfall 4: Substring matching false positives
**What goes wrong:** Pattern "k-1" matches "ok-1099" or sender pattern "chase" matches "purchase-chase-up@example.com".
**Why it happens:** Substring matching is inherently greedy. Short patterns match unexpected strings.
**How to avoid:** This is an acceptable tradeoff per CONTEXT.md -- patterns are user-configured and users can adjust. Document in config.example.yaml that shorter patterns are broader. Tests should verify expected behavior, not prevent it.
**Warning signs:** Users report unexpected matches. Add pattern length warnings in future if needed.

### Pitfall 5: UNIQUE constraint on insert needs proper error handling
**What goes wrong:** Inserting a duplicate `(message_id, account_email)` raises `sqlite3.IntegrityError`. If not caught, the entire scan crashes.
**Why it happens:** Expected behavior for dedup -- TECH_SPEC says catch IntegrityError and return None.
**How to avoid:** `try/except sqlite3.IntegrityError: return None` in `insert_email()`.
**Warning signs:** Scan crashes on second run with same emails.

### Pitfall 6: config.example.yaml location at runtime
**What goes wrong:** `init_config()` needs to find and copy config.example.yaml, but its location differs between dev (`./config.example.yaml`) and installed package (`site-packages/fnsvr/...`).
**Why it happens:** Installed packages don't preserve the repo directory structure.
**How to avoid:** Place config.example.yaml inside `src/fnsvr/` and use `importlib.resources` (Python 3.11+) or `Path(__file__).parent / "config.example.yaml"` to locate it. The pyproject.toml needs `[tool.setuptools.package-data]` to include YAML files.
**Warning signs:** `fnsvr init` works in dev but fails after `pip install`.

## Code Examples

### Config Path Resolution
```python
# Source: TECH_SPEC.md section 2.1
import os
from pathlib import Path

_DEFAULT_CONFIG_DIR = "~/.fnsvr"
_ENV_VAR = "FNSVR_CONFIG_DIR"

def get_config_dir() -> Path:
    """Return ~/.fnsvr or FNSVR_CONFIG_DIR env override."""
    env_dir = os.environ.get(_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser()
    return Path(_DEFAULT_CONFIG_DIR).expanduser()

def resolve_path(path_str: str) -> Path:
    """Expand ~ and $ENV_VARS in path strings."""
    return Path(os.path.expandvars(os.path.expanduser(path_str)))
```

### Storage Insert with Dedup
```python
# Source: TECH_SPEC.md section 2.3
import sqlite3

def insert_email(conn: sqlite3.Connection, email: dict) -> int | None:
    """Insert detected email. Returns row ID or None if duplicate."""
    try:
        cursor = conn.execute(
            """INSERT INTO detected_emails
               (message_id, account_name, account_email, category, priority,
                subject, sender, date_received, snippet, matched_pattern,
                has_attachments)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email["message_id"],
                email["account_name"],
                email["account_email"],
                email["category"],
                email["priority"],
                email["subject"],
                email["sender"],
                email["date_received"],
                email.get("snippet", "")[:500],  # Enforce 500 char limit
                email["matched_pattern"],
                email.get("has_attachments", 0),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
```

### Test Fixture Pattern
```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_config() -> dict:
    """Minimal valid config for testing."""
    return {
        "accounts": [
            {
                "name": "personal",
                "email": "test@gmail.com",
                "credentials_file": "credentials/personal_credentials.json",
                "token_file": "credentials/personal_token.json",
            }
        ],
        "paths": {
            "database": "~/test-fnsvr/data/fnsvr.db",
            "attachments": "~/test-fnsvr/data/attachments",
            "digests": "~/test-fnsvr/data/digests",
            "logs": "~/test-fnsvr/data/logs",
        },
        "categories": {
            "tax_documents": {
                "label": "Tax Documents",
                "priority": "critical",
                "subject_patterns": ["k-1", "1099", "w-2"],
                "sender_patterns": ["irs.gov", "turbotax"],
            }
        },
        "scan": {
            "initial_lookback_days": 90,
            "regular_lookback_days": 3,
            "max_results_per_scan": 100,
            "attachment_extensions": [".pdf", ".xlsx"],
        },
    }

@pytest.fixture
def db_conn(tmp_path):
    """Initialized in-memory-like test database."""
    from fnsvr.storage import init_db
    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    yield conn
    conn.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tempfile.mktemp()` in tests | pytest `tmp_path` fixture | pytest 3.9+ | Cleaner, auto-cleanup, no race conditions |
| `pkg_resources` for data files | `importlib.resources` | Python 3.9+ | No setuptools runtime dependency for finding package data |
| `os.path` string manipulation | `pathlib.Path` throughout | Python 3.6+ | Type-safe path ops, cleaner API |
| Manual `re.escape()` + `re.IGNORECASE` | Plain `str.lower()` + `in` | CONTEXT.md decision | Simpler, faster, no regex overhead for literal substrings |

**Deprecated/outdated:**
- `tempfile.mktemp()`: Still works but pytest `tmp_path` is superior for test isolation
- `pkg_resources`: Deprecated in favor of `importlib.resources` and `importlib.metadata`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (testpaths = ["tests"]) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --cov=fnsvr --cov-report=term-missing` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | init_config creates dir and copies config | unit | `pytest tests/test_config.py::test_init_config -x` | Wave 0 |
| CFG-02 | load_config validates accounts list | unit | `pytest tests/test_config.py::test_load_config_accounts -x` | Wave 0 |
| CFG-03 | load_config rejects missing keys | unit | `pytest tests/test_config.py::test_load_config_validation -x` | Wave 0 |
| CFG-04 | resolve_path expands ~ and $VARS | unit | `pytest tests/test_config.py::test_resolve_path -x` | Wave 0 |
| CFG-05 | get_config_dir respects FNSVR_CONFIG_DIR | unit | `pytest tests/test_config.py::test_config_dir_override -x` | Wave 0 |
| STOR-01 | init_db creates all 3 tables | unit | `pytest tests/test_storage.py::test_init_db -x` | Wave 0 |
| STOR-02 | WAL mode enabled after init | unit | `pytest tests/test_storage.py::test_wal_mode -x` | Wave 0 |
| STOR-03 | indexes exist on expected columns | unit | `pytest tests/test_storage.py::test_indexes -x` | Wave 0 |
| STOR-04 | snippet truncated to 500 chars on insert | unit | `pytest tests/test_storage.py::test_snippet_truncation -x` | Wave 0 |
| DET-01 | case-insensitive substring match | unit | `pytest tests/test_detector.py::test_case_insensitive -x` | Wave 0 |
| DET-02 | patterns from config only, no hardcoded | unit | `pytest tests/test_detector.py::test_compile_from_config -x` | Wave 0 |
| DET-03 | all 5 categories recognized | unit | `pytest tests/test_detector.py::test_five_categories -x` | Wave 0 |
| DET-04 | subject before sender, first match wins | unit | `pytest tests/test_detector.py::test_match_priority -x` | Wave 0 |
| DET-05 | DetectionMatch has all required fields | unit | `pytest tests/test_detector.py::test_detection_match_fields -x` | Wave 0 |
| DET-06 | duplicate insert returns None | unit | `pytest tests/test_storage.py::test_dedup_insert -x` | Wave 0 |
| TEST-01 | detector test suite passes | unit | `pytest tests/test_detector.py -v` | Wave 0 |
| TEST-02 | storage test suite passes | unit | `pytest tests/test_storage.py -v` | Wave 0 |
| TEST-03 | config test suite passes | unit | `pytest tests/test_config.py -v` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v --cov=fnsvr --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/fnsvr/__init__.py` -- package init with version
- [ ] `tests/__init__.py` -- empty package init
- [ ] `tests/conftest.py` -- shared fixtures (sample_config, db_conn)
- [ ] `pyproject.toml` -- must be at repo root (currently in Docs/)
- [ ] `config.example.yaml` inside `src/fnsvr/` for `importlib.resources` access
- [ ] Framework install: `pip install -e ".[dev]"`

## Open Questions

1. **config.example.yaml packaging location**
   - What we know: TECH_SPEC says it ships with the package. CLAUDE.md shows it at repo root level. pyproject.toml is in `Docs/`.
   - What's unclear: Should it live at repo root AND be copied into `src/fnsvr/` for package data, or just one location?
   - Recommendation: Place primary copy in `src/fnsvr/config.example.yaml` and reference via `importlib.resources`. Also keep a root-level symlink or copy for documentation purposes. Add `[tool.setuptools.package-data] fnsvr = ["config.example.yaml"]` to pyproject.toml.

2. **pyproject.toml location**
   - What we know: Currently in `Docs/pyproject.toml`. Must be at repo root for pip install to work.
   - What's unclear: Should the Docs/ copy be removed or kept as reference?
   - Recommendation: Move to repo root. Remove Docs/ copy to avoid drift.

3. **detector.py type adaptation**
   - What we know: TECH_SPEC defines `CompiledCategory` with `subject_patterns: list[re.Pattern]`. CONTEXT.md says use plain substring matching.
   - What's unclear: Should we keep `re.Pattern` type hints for forward compatibility?
   - Recommendation: Change to `list[str]` since we are storing lowercased strings, not compiled regex. This is honest about the actual data type.

## Sources

### Primary (HIGH confidence)
- TECH_SPEC.md -- Module contracts, function signatures, SQL schema, validation rules
- config.example.yaml -- Reference config with all 5 categories and ~70 patterns
- CONTEXT.md -- Locked decision on substring matching over regex
- pyproject.toml -- Package configuration, dependencies, tool settings

### Secondary (HIGH confidence)
- PyPI: PyYAML 6.0.3, pytest 9.0.2, ruff 0.15.8 -- verified via `pip3 index versions`
- Python 3.14.3 -- verified on system via `python3 --version`
- sqlite3 module -- stdlib, WAL support verified in Python docs

### Tertiary (LOW confidence)
- None -- all findings verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib + PyYAML, versions verified against PyPI
- Architecture: HIGH -- contracts fully defined in TECH_SPEC.md, patterns are standard Python
- Pitfalls: HIGH -- based on well-known Python/SQLite/YAML behaviors, not speculative

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no fast-moving dependencies)
