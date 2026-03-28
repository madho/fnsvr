---
phase: 04-automation-and-distribution
verified: 2026-03-28T21:00:00Z
status: gaps_found
score: 2/3 must-haves verified
re_verification: false
gaps:
  - truth: "User can install fnsvr via pip install fnsvr or brew install fnsvr and have the fnsvr command available on PATH"
    status: partial
    reason: "PyPI packaging is complete and the fnsvr entry point is correctly defined. Homebrew formula exists but cannot successfully install because it uses virtualenv_install_with_resources with no resource stanzas for Python dependencies (click, google-api-python-client, PyYAML, google-auth-oauthlib, google-auth-httplib2). A brew install would create an isolated virtualenv without dependencies, causing an import error on first run. The sha256 placeholder is documented as intentional, but the missing resource stanzas are a functional gap."
    artifacts:
      - path: "homebrew/fnsvr.rb"
        issue: "virtualenv_install_with_resources called but no resource stanzas defined for any of the 5 Python dependencies in pyproject.toml. Without resource blocks, Homebrew installs fnsvr into a virtualenv that has no installed dependencies."
    missing:
      - "resource stanzas for click, google-api-python-client, google-auth-oauthlib, google-auth-httplib2, PyYAML (with correct url and sha256 for each)"
      - "These are generated with brew-pip-audit or pip2homebrew and added before the def install block"
      - "Note: PLACEHOLDER_SHA256 for the package itself is separately acknowledged as intentional (post-PyPI-publish step)"
---

# Phase 4: Automation and Distribution Verification Report

**Phase Goal:** The tool runs unattended on a schedule and is installable in one command
**Verified:** 2026-03-28
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | launchd plists generated dynamically with absolute paths; install/uninstall via CLI commands | VERIFIED | scheduler.py generates plists via plistlib with `_find_fnsvr_binary()` for absolute path detection. CLI `schedule install/uninstall/status` commands are wired to `scheduler.install_schedule()`, `scheduler.uninstall_schedule()`, `scheduler.schedule_status()` at lines 253, 268, 283 of cli.py |
| 2 | Scan runs every 4 hours with RunAtLoad; digest generates weekly Monday 8am via launchd | VERIFIED | `generate_scan_plist` sets `StartInterval=14400` and `RunAtLoad=True`. `generate_digest_plist` sets `StartCalendarInterval={Weekday:1, Hour:8, Minute:0}`. Both verified by 9 unit tests in test_scheduler.py |
| 3 | User can install via pip install fnsvr or brew install fnsvr with fnsvr on PATH | PARTIAL | PyPI path: `pyproject.toml` has correct entry point `fnsvr = "fnsvr.cli:main"`, both sdist and wheel exist in `dist/`. PATH availability after `pip install` is confirmed by entry point definition. Homebrew path: formula exists but is non-functional (see Gaps below) |

**Score:** 2/3 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/fnsvr/scheduler.py` | plist generation, install/uninstall, status | VERIFIED | 157 lines, 6 functions: `_find_fnsvr_binary`, `_fnsvr_program_arguments`, `generate_scan_plist`, `generate_digest_plist`, `install_schedule`, `uninstall_schedule`, `schedule_status`. Fully implemented, no stubs. |
| `tests/test_scheduler.py` | Unit tests for plist content | VERIFIED | 9 tests: interval, calendar interval, absolute path, log paths, labels, binary path, program arguments (scan + digest). All collected and confirmed passing (96 total tests pass). |
| `src/fnsvr/cli.py` | `schedule` command group with install/uninstall/status | VERIFIED | Lines 244-289: `schedule` group added to `main`, three subcommands defined at lines 249/265/280. `import scheduler` at line 9. All three scheduler functions called. |
| `homebrew/fnsvr.rb` | Homebrew formula for brew install fnsvr | STUB | Formula exists with correct class structure, `virtualenv_install_with_resources`, and test block. But no `resource` stanzas for any of the 5 Python dependencies. Formula installs a broken empty virtualenv. |
| `MANIFEST.in` | sdist file inclusion | VERIFIED | 4 lines covering LICENSE, README.md, config.example.yaml, and `recursive-include src/fnsvr *.py *.yaml`. |
| `pyproject.toml` | PyPI-ready package configuration | VERIFIED | Entry point `fnsvr = "fnsvr.cli:main"`, all classifiers, URLs, dependencies, and package-data defined. Build artifacts confirmed in `dist/`: `fnsvr-0.1.0-py3-none-any.whl` and `fnsvr-0.1.0.tar.gz`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py schedule install` | `scheduler.install_schedule()` | direct call | WIRED | Line 253: `scan_path, digest_path = scheduler.install_schedule()` |
| `cli.py schedule uninstall` | `scheduler.uninstall_schedule()` | direct call | WIRED | Line 268: `scan_removed, digest_removed = scheduler.uninstall_schedule()` |
| `cli.py schedule status` | `scheduler.schedule_status()` | direct call | WIRED | Line 283: `state = scheduler.schedule_status()` |
| `scheduler.py install_schedule` | `get_config_dir()` | `from fnsvr.config import get_config_dir` | WIRED | Line 97: `log_dir = get_config_dir() / "data" / "logs"` |
| `scheduler.py generate_scan_plist` | `_fnsvr_program_arguments()` | internal call | WIRED | Line 56: `"ProgramArguments": _fnsvr_program_arguments(binary_path, "scan")` |
| `scheduler.py generate_digest_plist` | `_fnsvr_program_arguments()` | internal call | WIRED | Line 73: `"ProgramArguments": _fnsvr_program_arguments(binary_path, "digest")` |
| `pyproject.toml [project.scripts]` | `fnsvr.cli:main` | entry point declaration | WIRED | `fnsvr = "fnsvr.cli:main"` and `def main()` exists at line 15 of cli.py |
| `homebrew/fnsvr.rb virtualenv_install_with_resources` | Python dependency packages | resource stanzas | NOT_WIRED | No resource blocks exist. Dependencies declared in pyproject.toml (click, google-api-python-client, etc.) are not available to the formula. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SCHED-01 | 04-01 | launchd plist for scanning every 4 hours with RunAtLoad | SATISFIED | `generate_scan_plist`: `StartInterval=14400`, `RunAtLoad=True`; tested in `test_scan_plist_contains_correct_interval` |
| SCHED-02 | 04-01 | launchd plist for weekly digest generation (Monday 8am) | SATISFIED | `generate_digest_plist`: `StartCalendarInterval={Weekday:1, Hour:8, Minute:0}`; tested in `test_digest_plist_contains_calendar_interval` |
| SCHED-03 | 04-01 | Plists generated dynamically with absolute binary paths | SATISFIED | `_find_fnsvr_binary()` cascades: `shutil.which` -> sibling -> `sys.executable`; `Path.resolve()` ensures absolute; tested in `test_plist_has_absolute_binary_path` and `test_find_fnsvr_binary_returns_absolute_path` |
| SCHED-04 | 04-01 | User can install/uninstall scheduling via CLI commands | SATISFIED | `fnsvr schedule install/uninstall/status` subcommands wired to scheduler module; no manual launchctl needed |
| DIST-01 | 04-02 | Package installable via pip install fnsvr from PyPI | SATISFIED (pre-publish) | pyproject.toml complete, entry point defined, dist/ contains sdist + wheel. Actual PyPI upload pending but build is verified. |
| DIST-02 | 04-02 | Homebrew tap formula for brew install fnsvr | BLOCKED | Formula exists but missing resource stanzas for all Python dependencies. `brew install` would produce a broken install. |
| DIST-03 | 04-02 | Entry point fnsvr available on PATH after install | SATISFIED | `[project.scripts] fnsvr = "fnsvr.cli:main"` correctly maps to `def main()` in cli.py. pip install places this on PATH. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `homebrew/fnsvr.rb` | 11 | `sha256 "PLACEHOLDER_SHA256"` | Info | Intentional pre-publication placeholder. Documented in SUMMARY. Not a code stub -- replaced when publishing to PyPI. |
| `homebrew/fnsvr.rb` | 17 | `virtualenv_install_with_resources` with zero `resource` blocks | Blocker | `brew install fnsvr` installs an isolated virtualenv containing only the fnsvr package itself, without click, google-api-python-client, PyYAML, or google-auth-* packages. Running `fnsvr` would fail immediately with `ModuleNotFoundError`. |

---

### Human Verification Required

None -- all checks are automatable via grep and file inspection. The formula gap is confirmed programmatically (zero `resource` lines outside the `virtualenv_install_with_resources` call).

---

### Gaps Summary

**1 functional gap blocking full goal achievement.**

The phase goal is "installable in one command." PyPI packaging satisfies `pip install fnsvr` -- the entry point is correct, the build artifacts exist, and the package structure is complete. The `fnsvr` binary would be on PATH after pip install.

The Homebrew path (`brew install fnsvr`) is broken. The formula uses `Language::Python::Virtualenv` and calls `virtualenv_install_with_resources`, which is the correct Homebrew pattern for Python packages. However, this method requires the formula to declare each Python dependency as a `resource` block with a URL and sha256. Without those blocks, the install succeeds structurally (a virtualenv is created, fnsvr is installed into it) but the installed binary immediately crashes because none of its imports (`click`, `google.auth`, `yaml`, etc.) are present in the isolated virtualenv.

A complete formula would have 5-10 resource stanzas generated by `brew-pip-audit` or `pip2homebrew` after the package is published to PyPI. The SUMMARY notes the sha256 placeholder as intentional, but the missing resource stanzas were not flagged as a known stub -- they are a functional incompleteness that prevents DIST-02 from being satisfied.

The SCHED-01 through SCHED-04 requirements are fully satisfied. The core unattended scheduling story (the primary part of the phase goal) is complete and correct.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
