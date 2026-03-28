# Roadmap: fnsvr

## Overview

fnsvr delivers a local-first CLI tool that monitors multiple Gmail accounts for financial emails and surfaces them through macOS notifications, markdown digests, and an interactive review workflow. The build follows a strict dependency graph: foundation modules first (config, storage, detector), then Gmail integration (the critical path with real OAuth risk), then user-facing output that consumes stored detections, then automation and packaging, with the landing page built in parallel whenever convenient.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Config loading, SQLite storage, and pattern detection engine with unit tests (completed 2026-03-28)
- [ ] **Phase 2: Gmail Integration** - OAuth setup, multi-account scanning, attachment downloading
- [ ] **Phase 3: User-Facing Output** - Notifications, digest generation, interactive review, and stats
- [ ] **Phase 4: Automation and Distribution** - launchd scheduling, PyPI packaging, Homebrew formula
- [ ] **Phase 5: Landing Page** - Single-file fnsvr.com site (parallel with any phase)

## Phase Details

### Phase 1: Foundation
**Goal**: The three core modules (config, storage, detector) are built, tested, and ready to receive real Gmail data
**Depends on**: Nothing (first phase)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, STOR-01, STOR-02, STOR-03, STOR-04, DET-01, DET-02, DET-03, DET-04, DET-05, DET-06, TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. User can run `fnsvr init` and get a working config directory with example config at ~/.fnsvr/
  2. Config loads from YAML, validates required keys, rejects invalid files with clear errors, and resolves ~ and $ENV paths
  3. SQLite database initializes with correct schema (detected_emails, attachments, scan_log), WAL mode, and proper indexes
  4. Detector matches email subjects/senders against config-defined patterns with correct category assignment, priority ordering, and deduplication
  5. Unit tests pass for config loading, storage CRUD, and detector pattern matching (TEST-01, TEST-02, TEST-03)
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md -- Project scaffold, config.py module, and config unit tests
- [x] 01-02-PLAN.md -- SQLite storage layer with schema, CRUD, and unit tests
- [x] 01-03-PLAN.md -- Pattern detection engine with pure functions and unit tests

### Phase 2: Gmail Integration
**Goal**: Users can authenticate Gmail accounts and scan them for financial emails with attachments downloaded automatically
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, SCAN-01, SCAN-02, SCAN-03, SCAN-04, SCAN-05, SCAN-06, ATT-01, ATT-02, ATT-03, ATT-04, ATT-05
**Success Criteria** (what must be TRUE):
  1. User can run `fnsvr setup <account>` to complete browser-based OAuth for a Gmail account, with tokens stored at 600 permissions using gmail.readonly scope only
  2. User can run `fnsvr scan` and see financial emails detected across all configured accounts, with errors in one account not blocking others
  3. Scan supports --initial (90-day), --days N (custom), and --account (single account) flags, and every scan is logged with timing and counts
  4. PDF and spreadsheet attachments from detected emails are auto-downloaded to organized directories with no overwrites and failed downloads logged but non-blocking
  5. Expired OAuth tokens auto-refresh silently; failed refresh produces a clear error directing user to re-run setup
**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md -- OAuth authentication and multi-account scan orchestration (scanner.py + tests)
- [x] 02-02-PLAN.md -- Attachment downloading with MIME traversal and safe file handling (downloader.py + tests)
- [x] 02-03-PLAN.md -- Wire scanner + downloader together and create CLI commands (cli.py + integration tests)

### Phase 3: User-Facing Output
**Goal**: The tool delivers actionable output -- notifications alert on new detections, digests summarize activity, review enables triage, stats give quick status
**Depends on**: Phase 2
**Requirements**: NOTF-01, NOTF-02, NOTF-03, NOTF-04, NOTF-05, DIG-01, DIG-02, DIG-03, DIG-04, DIG-05, DIG-06, DIG-07, REV-01, REV-02, REV-03, REV-04, REV-05, REV-06, STAT-01, STAT-02, TEST-04
**Success Criteria** (what must be TRUE):
  1. macOS notifications fire for new detections with priority-appropriate sounds, batch summarization when count exceeds threshold, and graceful degradation on non-macOS
  2. User can run `fnsvr digest` and get a markdown report grouped by category with summary counts, action-required section for unreviewed critical items, and optional Obsidian vault sync
  3. User can run `fnsvr review` to interactively triage unreviewed items (mark reviewed with notes, skip, quit, mark-all), filterable by category and account
  4. User can run `fnsvr stats` for instant terminal summary of tracked items, unreviewed counts, and breakdowns -- with zero Gmail API calls
  5. Unit tests pass for digest generation (TEST-04)
**Plans:** 4 plans

Plans:
- [ ] 03-01-PLAN.md -- macOS notification module and scanner integration
- [ ] 03-02-PLAN.md -- Markdown digest generator with storage helper and unit tests
- [ ] 03-03-PLAN.md -- Interactive review module
- [ ] 03-04-PLAN.md -- CLI commands for digest, review, and stats

### Phase 4: Automation and Distribution
**Goal**: The tool runs unattended on a schedule and is installable in one command
**Depends on**: Phase 3
**Requirements**: SCHED-01, SCHED-02, SCHED-03, SCHED-04, DIST-01, DIST-02, DIST-03
**Success Criteria** (what must be TRUE):
  1. launchd plists are generated dynamically with absolute paths and install/uninstall via CLI commands (no manual plist editing or launchctl)
  2. Scan runs automatically every 4 hours and digest generates weekly (Monday 8am) via launchd with RunAtLoad
  3. User can install fnsvr via `pip install fnsvr` or `brew install fnsvr` and have the `fnsvr` command available on PATH
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Landing Page
**Goal**: fnsvr.com exists as a trust signal and getting-started resource for new users
**Depends on**: Nothing (can be built in parallel with any phase)
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05
**Success Criteria** (what must be TRUE):
  1. Single index.html file under 30KB with dark terminal aesthetic, monospace code, warm amber accents
  2. Page includes all required sections: hero, problem statement, 5-category feature grid, 3-step how-it-works, design principles, quick-start terminal block, footer
  3. Zero analytics, zero tracking, zero cookies, zero JS frameworks -- deployable to GitHub Pages or Vercel with no build step
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order (1 through 4 sequentially). Phase 5 can execute in parallel with any phase.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete   | 2026-03-28 |
| 2. Gmail Integration | 0/3 | Planned | - |
| 3. User-Facing Output | 0/4 | Planned | - |
| 4. Automation and Distribution | 0/2 | Not started | - |
| 5. Landing Page | 0/1 | Not started | - |
