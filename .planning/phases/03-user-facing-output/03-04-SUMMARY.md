---
phase: 03-user-facing-output
plan: 04
subsystem: cli
tags: [click, cli, python]

requires:
  - phase: 03-02
    provides: digest generation and save functions
  - phase: 03-03
    provides: interactive review and mark_all functions
provides:
  - CLI commands for digest, review, and stats accessible via fnsvr binary
affects: [04-scheduling, 05-landing-page]

tech-stack:
  added: []
  patterns: [consistent CLI command pattern with config load, db init, try/finally close]

key-files:
  created: []
  modified: [src/fnsvr/cli.py]

key-decisions:
  - "Followed existing CLI pattern: load config, init db, try/finally close for all three commands"
  - "stats command uses plain click.echo with terminal formatting, no markdown (per CONTEXT.md)"

patterns-established:
  - "CLI command pattern: load config, resolve db path, init_db, try/finally conn.close"

requirements-completed: [STAT-01, STAT-02]

duration: 1min
completed: 2026-03-28
---

# Phase 3 Plan 4: CLI Commands for Digest, Review, and Stats Summary

**Wired digest, review, and stats commands into Click CLI completing all Phase 3 user-facing output modules**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-28T20:15:53Z
- **Completed:** 2026-03-28T20:17:18Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `fnsvr digest` command with --days, --unreviewed, --no-save flags
- Added `fnsvr review` command with --category, --account, --mark-all flags
- Added `fnsvr stats` command for terminal summary (zero Gmail API calls)
- All 6 CLI commands (init, setup, scan, digest, review, stats) registered and verified
- All 87 existing tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add digest command to cli.py** - `fc6e576` (feat)
2. **Task 2: Add review and stats commands to cli.py** - `ea86dbb` (feat)

## Files Created/Modified
- `src/fnsvr/cli.py` - Added digest, review, stats commands with proper option flags and config/db lifecycle

## Decisions Made
- Followed existing CLI pattern exactly: load config, init db, try/finally close
- stats command uses clean terminal output with click.echo (no markdown formatting per CONTEXT.md)
- review command delegates to reviewer.review_interactive or reviewer.mark_all based on --mark-all flag

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 3 commands are wired and accessible
- Phase 4 (scheduling/launchd) can proceed -- scan command is ready for background execution
- All CLI entry points complete for v0.1

---
*Phase: 03-user-facing-output*
*Completed: 2026-03-28*
