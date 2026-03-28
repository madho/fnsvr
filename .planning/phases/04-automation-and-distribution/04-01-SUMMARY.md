---
phase: 04-automation-and-distribution
plan: 01
subsystem: scheduling
tags: [launchd, plistlib, macOS, automation]

requires:
  - phase: 01-foundation
    provides: config.py get_config_dir for log directory resolution
provides:
  - scheduler.py module with plist generation, install, uninstall, status
  - CLI schedule group with install/uninstall/status subcommands
affects: [04-02-homebrew-formula]

tech-stack:
  added: [plistlib (stdlib)]
  patterns: [plistlib.dumps for XML generation, shutil.which for binary detection]

key-files:
  created: [src/fnsvr/scheduler.py, tests/test_scheduler.py]
  modified: [src/fnsvr/cli.py]

key-decisions:
  - "Used plistlib from stdlib for plist XML generation (not string templates)"
  - "Binary detection: shutil.which -> sys.executable sibling -> python -m fallback"
  - "Module fallback uses [python, -m, fnsvr, cmd] for ProgramArguments"

patterns-established:
  - "Platform-specific modules check platform.system() and raise RuntimeError for unsupported OS"
  - "CLI groups for multi-level subcommands (main -> schedule -> install/uninstall/status)"

requirements-completed: [SCHED-01, SCHED-02, SCHED-03, SCHED-04]

duration: 2min
completed: 2026-03-28
---

# Phase 04 Plan 01: launchd Scheduling Summary

**launchd plist generation with plistlib, CLI schedule commands, and 9 unit tests for interval/path/label verification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T20:24:44Z
- **Completed:** 2026-03-28T20:27:04Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- scheduler.py with 6 functions: _find_fnsvr_binary, generate_scan_plist, generate_digest_plist, install_schedule, uninstall_schedule, schedule_status
- Plist generation via plistlib (not string concatenation) with absolute paths throughout
- CLI schedule group with install, uninstall, and status subcommands
- 9 unit tests verifying plist content: intervals, calendar intervals, absolute paths, log paths, labels, program arguments

## Task Commits

Each task was committed atomically:

1. **Task 1: Create scheduler.py with TDD** - `6b52641` (test: RED), `75a3947` (feat: GREEN)
2. **Task 2: Wire schedule commands into CLI** - `dfb55d9` (feat)

## Files Created/Modified
- `src/fnsvr/scheduler.py` - Plist generation, install/uninstall, status logic
- `tests/test_scheduler.py` - 9 unit tests for plist content verification
- `src/fnsvr/cli.py` - Added schedule group with install/uninstall/status subcommands

## Decisions Made
- Used plistlib.dumps() from stdlib for XML generation instead of string templates -- produces valid Apple plist XML reliably
- Binary detection cascades: shutil.which("fnsvr") -> sys.executable sibling -> python -m fnsvr fallback
- When falling back to module mode, ProgramArguments becomes [python, -m, fnsvr, subcommand] for correct execution

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None -- no external service configuration required.

## Known Stubs
None -- all functions are fully implemented.

## Next Phase Readiness
- Scheduler module complete, ready for Homebrew formula (04-02) to package the schedule commands
- install_schedule creates log directory automatically, so users just run `fnsvr schedule install`

---
*Phase: 04-automation-and-distribution*
*Completed: 2026-03-28*
