---
phase: 01-foundation
plan: 01
subsystem: config
tags: [python, pyyaml, setuptools, config, packaging]

# Dependency graph
requires: []
provides:
  - "Installable fnsvr Python package (pip install -e '.[dev]')"
  - "config.py module with load/validate/init/resolve functions"
  - "config.example.yaml bundled as package data"
  - "Test fixtures (sample_config, db_conn) for all future test files"
affects: [01-02, 01-03, 02-scanner, 02-detector]

# Tech tracking
tech-stack:
  added: [PyYAML, pytest, ruff, setuptools, click, google-api-python-client]
  patterns: [src-layout packaging, TDD red-green-refactor, monkeypatch for env isolation]

key-files:
  created:
    - pyproject.toml
    - src/fnsvr/__init__.py
    - src/fnsvr/config.py
    - src/fnsvr/config.example.yaml
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_config.py
    - .gitignore
  modified: []

key-decisions:
  - "Used Path(__file__).parent to locate bundled config.example.yaml (works in editable and installed mode)"
  - "os.path.expandvars + expanduser for resolve_path (pathlib expanduser alone does not handle $ENV_VARS)"
  - "Validation fails fast: FileNotFoundError for missing file, ValueError for bad YAML or missing keys"

patterns-established:
  - "src-layout: all source in src/fnsvr/, tests in tests/"
  - "Config env override: FNSVR_CONFIG_DIR overrides default ~/.fnsvr"
  - "Test isolation: monkeypatch for env vars, tmp_path for filesystem"

requirements-completed: [CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, TEST-03]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 01 Plan 01: Package Scaffold and Config Module Summary

**Installable fnsvr package with config loading, YAML validation, path resolution, and init_config -- 14 passing tests via TDD**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T19:33:33Z
- **Completed:** 2026-03-28T19:36:08Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Installable Python package with `pip install -e ".[dev]"` working out of the box
- config.py with all 6 functions matching TECH_SPEC.md contracts: get_config_dir, get_config_path, load_config, resolve_path, ensure_dirs, init_config
- 14 unit tests covering all config behaviors including edge cases (empty files, missing keys, env overrides, force overwrite)
- config.example.yaml bundled as package data for init_config to copy

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold and config.example.yaml** - `bf70758` (feat)
2. **Task 2 RED: Failing tests for config module** - `7b9045e` (test)
3. **Task 2 GREEN: config.py implementation** - `5e1b37d` (feat)

## Files Created/Modified
- `pyproject.toml` - Package build config with setuptools, deps, package-data
- `src/fnsvr/__init__.py` - Package init with __version__ = "0.1.0"
- `src/fnsvr/config.py` - Config loading, validation, path resolution, init
- `src/fnsvr/config.example.yaml` - Reference config with 5 detection categories
- `tests/__init__.py` - Test package marker
- `tests/conftest.py` - Shared fixtures: sample_config, db_conn
- `tests/test_config.py` - 14 unit tests for config module
- `.gitignore` - Python project ignores

## Decisions Made
- Used `Path(__file__).parent` to locate bundled config.example.yaml rather than importlib.resources (simpler, works in both editable and installed mode)
- `os.path.expandvars(os.path.expanduser())` for resolve_path since pathlib's expanduser does not handle $ENV_VARS
- Validation fails fast with specific exceptions: FileNotFoundError for missing file, ValueError with descriptive messages for bad YAML or missing keys

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed false positive in test_init_config_force assertion**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Test asserted `"old" not in content` but "old" appears in "lookback" within config.example.yaml
- **Fix:** Changed assertion to `"old: true" not in content` for precise matching
- **Files modified:** tests/test_config.py
- **Verification:** All 14 tests pass
- **Committed in:** 5e1b37d (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test assertion fix. No scope creep.

## Issues Encountered
- Homebrew Python required venv creation (PEP 668 externally-managed restriction). Created venv/ in project root, already covered by .gitignore.

## Known Stubs
None -- all functions are fully implemented with no placeholder code.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Package scaffold complete, ready for storage.py (01-02) and detector.py (01-03)
- test fixtures (sample_config, db_conn) available for all future test files
- config.example.yaml bundled and accessible at runtime

## Self-Check: PASSED

All 8 files verified present. All 3 commits verified in git log.

---
*Phase: 01-foundation*
*Completed: 2026-03-28*
