---
phase: 03-user-facing-output
plan: 01
subsystem: notifications
tags: [osascript, macos, notifications, subprocess]

requires:
  - phase: 02-gmail-integration
    provides: scanner.scan_account with detection loop and storage.insert_email
provides:
  - notifier.py module with macOS notification support via osascript
  - Scanner wired to send notifications after new detections
affects: [03-user-facing-output, 04-cli-launchd]

tech-stack:
  added: [osascript (system), platform, subprocess]
  patterns: [silent-failure notification pattern, config-driven notification batching]

key-files:
  created: [src/fnsvr/notifier.py]
  modified: [src/fnsvr/scanner.py]

key-decisions:
  - "Notifications never block scanning -- all errors caught with try/except"
  - "Batch threshold from config controls individual vs summary notification mode"
  - "Category labels derived from category key via replace/title (no extra config field needed)"

patterns-established:
  - "Silent failure for platform-specific features: check platform.system(), log debug, return gracefully"
  - "Side-effect calls wrapped in try/except after main loop, not inline with processing"

requirements-completed: [NOTF-01, NOTF-02, NOTF-03, NOTF-04, NOTF-05]

duration: 2min
completed: 2026-03-28
---

# Phase 3 Plan 1: Notification Module Summary

**macOS native notifications via osascript with priority-based sounds, config-driven batching, and scanner integration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T20:12:54Z
- **Completed:** 2026-03-28T20:14:15Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created notifier.py with notify() and notify_detections() functions
- Individual notifications for low-volume detections with category-specific titles
- Summary notifications when detections exceed batch_threshold
- Priority-based sounds: Submarine for critical, Pop for normal
- Wired notifier into scanner.scan_account after detection loop
- Non-macOS platforms handled gracefully with debug logging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create notifier.py module** - `dd840dd` (feat)
2. **Task 2: Wire notifier into scanner.scan_account** - `71fd4fc` (feat)

## Files Created/Modified
- `src/fnsvr/notifier.py` - macOS notification module with notify() and notify_detections()
- `src/fnsvr/scanner.py` - Added notifier import, new_detections collection, and notification call

## Decisions Made
- Notifications never block scanning -- all errors caught with try/except at both module and call-site level
- Category labels derived from category key (e.g. "tax_documents" -> "Tax Documents") rather than requiring a separate config field
- Batch threshold comparison uses strict greater-than (not >=) matching the plan specification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented.

## Next Phase Readiness
- Notification module complete, ready for digest (03-02) and CLI wiring (03-04)
- Scanner now produces user-visible output for new detections

---
*Phase: 03-user-facing-output*
*Completed: 2026-03-28*
