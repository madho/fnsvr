---
phase: 02-gmail-integration
plan: 03
subsystem: cli
tags: [click, cli, gmail-api, downloader, scanner, integration]

# Dependency graph
requires:
  - phase: 02-01
    provides: "scanner.py with OAuth auth, scan_account, scan_all"
  - phase: 02-02
    provides: "downloader.py with process_attachments, walk_parts"
provides:
  - "cli.py with init, setup, scan Click commands"
  - "scanner.py wired to downloader.process_attachments"
  - "Full scan-detect-download pipeline"
affects: [03-notifications, 04-digest-review]

# Tech tracking
tech-stack:
  added: [click]
  patterns: [cli-entry-point, module-wiring, lookback-flag-priority]

key-files:
  created: [src/fnsvr/cli.py]
  modified: [src/fnsvr/scanner.py, tests/test_scanner.py]

key-decisions:
  - "Lookback priority order: --days > --initial > config default (3 days)"
  - "Attachment save_dir and allowed_ext resolved once per scan_account, not per message"
  - "CLI setup validates account name against config before calling OAuth flow"

patterns-established:
  - "CLI wiring: each command loads config, resolves paths, calls module functions"
  - "Error display: errors go to stderr via click.echo(err=True), success to stdout"

requirements-completed: [AUTH-01, SCAN-01, SCAN-02, SCAN-03, SCAN-04, ATT-01]

# Metrics
duration: 2min
completed: 2026-03-28
---

# Phase 02 Plan 03: CLI + Scanner-Downloader Wiring Summary

**Click CLI with init/setup/scan commands wiring scanner and downloader into a complete scan-detect-download pipeline**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T20:01:03Z
- **Completed:** 2026-03-28T20:03:23Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created cli.py with init, setup, and scan Click commands supporting all flags (--initial, --days N, --account)
- Wired downloader.process_attachments into scanner.scan_account so detected emails get attachments downloaded automatically
- Added 6 integration tests verifying the full scan+download pipeline and CLI flag behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire downloader into scanner.py and create cli.py** - `efdf625` (feat)
2. **Task 2: Add integration-level tests for scan + download pipeline** - `2673ca9` (test)

## Files Created/Modified
- `src/fnsvr/cli.py` - Click CLI entry point with init, setup, scan commands
- `src/fnsvr/scanner.py` - Updated scan_account to call downloader.process_attachments after detection
- `tests/test_scanner.py` - 6 new integration tests (scan+download, account filter, lookback flags, setup errors)

## Decisions Made
- Lookback priority order: --days > --initial > config default (3 days) -- matches TECH_SPEC.md requirements
- Attachment save_dir and allowed_ext resolved once at start of scan_account (not per message) for efficiency
- CLI setup validates account name against config before calling scanner.setup_oauth to fail fast with clear message

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all CLI commands are wired to real implementations.

## Next Phase Readiness
- Phase 02 Gmail Integration is now complete (all 3 plans done)
- Full pipeline: config -> scan -> detect -> download works end-to-end
- Ready for Phase 03 (notifications) which will hook into scan results
- Ready for Phase 04 (digest/review) which will query stored detections

---
*Phase: 02-gmail-integration*
*Completed: 2026-03-28*

## Self-Check: PASSED
