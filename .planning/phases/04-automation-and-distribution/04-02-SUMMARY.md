---
phase: 04-automation-and-distribution
plan: 02
subsystem: infra
tags: [pypi, homebrew, packaging, distribution, setuptools]

# Dependency graph
requires:
  - phase: 03-user-interaction
    provides: Complete CLI with all commands (scan, review, digest, stats, init, setup)
provides:
  - MANIFEST.in for sdist inclusion of config and source files
  - Homebrew tap formula for brew install fnsvr
  - Verified PyPI-ready build (sdist + wheel)
affects: [05-landing-page]

# Tech tracking
tech-stack:
  added: [python-build]
  patterns: [MANIFEST.in for sdist, Homebrew virtualenv_install_with_resources]

key-files:
  created:
    - MANIFEST.in
    - homebrew/fnsvr.rb
  modified: []

key-decisions:
  - "pyproject.toml already complete -- no changes needed, only verification"
  - "Homebrew formula uses virtualenv_install_with_resources for clean isolation"
  - "sha256 placeholder in formula to be updated on actual PyPI publish"

patterns-established:
  - "MANIFEST.in pattern: include LICENSE, README, config, recursive-include src"
  - "Homebrew formula pattern: Language::Python::Virtualenv with depends_on python@3.12"

requirements-completed: [DIST-01, DIST-02, DIST-03]

# Metrics
duration: 1min
completed: 2026-03-28
---

# Phase 04 Plan 02: PyPI Packaging and Homebrew Formula Summary

**MANIFEST.in for sdist and Homebrew tap formula enabling pip install and brew install fnsvr**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-28T20:24:47Z
- **Completed:** 2026-03-28T20:26:03Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created MANIFEST.in ensuring sdist includes LICENSE, README, config, and all source files
- Verified pip install -e . succeeds and fnsvr --help shows all 6 commands
- Verified python -m build produces both sdist and wheel in dist/
- Created Homebrew tap formula with valid Ruby syntax for brew install fnsvr

## Task Commits

Each task was committed atomically:

1. **Task 1: Finalize pyproject.toml for PyPI and verify build** - `b252320` (chore)
2. **Task 2: Create Homebrew tap formula** - `30b00ab` (feat)

## Files Created/Modified
- `MANIFEST.in` - Ensures sdist includes LICENSE, README, config.example.yaml, and all Python/YAML source files
- `homebrew/fnsvr.rb` - Homebrew formula with virtualenv install, python@3.12 dep, and test block

## Decisions Made
- pyproject.toml was already fully configured with entry point, URLs, classifiers, and package-data -- no changes needed
- Homebrew formula uses PLACEHOLDER_SHA256 to be replaced when publishing to PyPI
- Formula depends on python@3.12 (most common Homebrew Python)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Known Stubs

- `homebrew/fnsvr.rb` line 10: `sha256 "PLACEHOLDER_SHA256"` -- intentional placeholder, updated when publishing to PyPI (not a code stub)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PyPI packaging verified and ready for `twine upload`
- Homebrew formula ready to copy to madho/homebrew-fnsvr tap repo after PyPI publish
- Phase 05 (landing page) has no code dependencies on this plan

---
*Phase: 04-automation-and-distribution*
*Completed: 2026-03-28*
