# fnsvr

## What This Is

fnsvr ("fin-sever") is a local-first CLI tool for macOS that scans multiple Gmail accounts for financial emails -- K1s, 1099s, signature requests, wire confirmations, equity grants, brokerage statements -- and makes sure nothing important slips through. It runs as a background process, stores everything locally in SQLite, sends macOS notifications for urgent items, and generates weekly markdown digests. Accompanied by a single-page landing site (fnsvr.com) explaining what it is and how to get started.

Built for busy founders, investors, and execs with 3-5+ Gmail accounts and complex financial lives who don't have a family office or dedicated admin catching this for them.

## Core Value

Financial emails with real deadlines and real dollar consequences must never go unnoticed, regardless of which inbox they landed in.

## Requirements

### Validated

(None yet -- ship to validate)

### Active

- [ ] Multi-account Gmail scanning on a 4-hour schedule via launchd
- [ ] Pattern-based detection across 5 categories: tax docs, signature requests, equity grants, brokerage statements, bank/wire confirmations
- [ ] All detection patterns config-driven in YAML (no hardcoded patterns)
- [ ] Auto-download of PDF/spreadsheet attachments from detected emails
- [ ] macOS native notifications with priority-based alerting (critical vs high)
- [ ] Weekly markdown digest with optional Obsidian vault sync
- [ ] Interactive review workflow with audit trail (reviewed/unreviewed status + notes)
- [ ] Quick terminal stats command
- [ ] Guided setup: `fnsvr init` creates config, `fnsvr setup <account>` opens browser for Google OAuth (like gcloud auth login)
- [ ] Homebrew formula for single-command install (`brew install fnsvr`)
- [ ] launchd auto-configuration (no manual plist editing)
- [ ] Landing page: single self-contained HTML file, dark terminal aesthetic, under 30KB, no JS frameworks, no analytics/tracking

### Out of Scope

- GUI or web dashboard -- this is a CLI tool, meet power users in the terminal
- Outlook / Microsoft Graph API -- Gmail only for v0.1
- IMAP support -- Gmail API is the right abstraction for this audience
- AI/LLM classification -- pattern matching is simple, auditable, and fast
- Email sending or modification -- read-only is a trust decision, not a limitation
- Cloud sync or multi-device -- local-first is the point
- Mobile notifications (push, SMS) -- macOS notifications are sufficient for the Mac-based workflow
- Encryption at rest for SQLite -- v0.1, revisit later
- Email digest delivery -- macOS notifs + Obsidian + terminal is enough
- Shared OAuth app / auth relay service -- users authenticate directly with Google, no intermediary

## Context

### Target Persona

Composite of three real people: a GTM consultant/founder running multiple ventures (Brooklyn), a co-founder of a billion-dollar network who angel invests (NYC), and a former COO of Venmo running a fintech VC fund (Philly/NYC). They share:

- 3-5+ Gmail accounts across personal, business, investing, board roles
- Complex financial lives with K1s, equity grants, DocuSigns, wire confirmations
- No family office or admin -- they handle it themselves
- Technically comfortable (terminal, GitHub, YAML) but not writing code daily
- The consequence of missing something is real money or dead deals

### What They Care About

1. **Privacy.** Real assets. Not handing email access to a cloud service.
2. **Simplicity.** Install once, configure once, forget it exists until it saves them.
3. **Control.** Add their own brokers/banks via config. Don't wait for a product team.

### Existing Spec Documents

Full specs exist in `Docs/`:
- `VISION.md` -- design principles and north star
- `PRD.md` -- user stories and acceptance criteria
- `TECH_SPEC.md` -- architecture, module contracts, data model
- `CLAUDE.md` -- build instructions and CLI commands
- `config.example.yaml` -- reference config with all detection patterns
- `pyproject.toml` -- packaging config
- `CONTRIBUTING.md` -- contribution guidelines

### Website Spec

Single-page site at fnsvr.com. Terminal-native / editorial minimalist aesthetic (think httpie.io, charm.sh, early Linear). Dark background, monospace for code, warm amber accents. Single HTML file, inline CSS, vanilla JS at most (typing effect). No analytics, no cookies, no build step. Structure: hero, problem statement, feature grid (5 categories), 3-step how-it-works, design principles, quick-start terminal block, footer.

## Constraints

- **Tech stack**: Python 3.11+, Click CLI, SQLite (no ORM), google-api-python-client (gmail.readonly only), PyYAML, macOS osascript for notifications, launchd for scheduling
- **Privacy**: gmail.readonly scope only. No email content stored beyond subject/snippet. No data transmitted externally. OAuth tokens stored with 600 permissions
- **Platform**: macOS primary. Core logic (scan, detect, store, digest) should be cross-platform. Platform-specific code (notifications, launchd) isolated in dedicated modules
- **Dependencies**: Minimal. Only google-api-python-client, google-auth-oauthlib, click, pyyaml
- **Website**: Single index.html under 30KB. No frameworks. No tracking. Deployable to GitHub Pages or Vercel
- **Install**: Must support `brew install fnsvr` for non-engineer users

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-first, no cloud | Target users have real assets and won't trust a cloud service with email access | -- Pending |
| gmail.readonly scope only | Trust decision: users should never worry about what fnsvr might do to their inbox | -- Pending |
| Browser-based OAuth flow (like gcloud auth login) | Avoids requiring users to create GCP projects or navigate cloud console | -- Pending |
| Homebrew for install | Target user can run `brew install` but shouldn't need to manage Python venvs | -- Pending |
| macOS notifications only (no email digest) | Keeps it local-first pure. Digest goes to Obsidian or terminal | -- Pending |
| Config-driven patterns in YAML | Adding a new bank/broker should be a one-line edit, not a code change | -- Pending |
| Website as single HTML file | Consistent with the tool's philosophy: simple, fast, no dependencies | -- Pending |
| Full PRD scope for v0.1 | Spec is already well-scoped. Ship scan + detect + download + notify + digest + review | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after initialization*
