# Feature Landscape

**Domain:** Local-first CLI financial email monitor for multi-account Gmail users
**Researched:** 2026-03-28

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-account Gmail scanning | Core value prop -- the whole point is cross-inbox coverage. Target persona has 3-5+ accounts | High | OAuth per account, token refresh, error isolation. Gmail API rate limits apply (~250 quota units per user per second). Each account authenticates independently |
| Pattern-based financial email detection | Users need reliable identification of K1s, 1099s, wire confirmations, DocuSign requests, equity grants across 5 categories | Medium | Substring/regex on subject + sender. Case-insensitive. Config-driven so users extend. First-match-wins across categories |
| Config-driven YAML patterns | Target users are "technically comfortable but not writing code daily" -- YAML edits are their ceiling for customization | Low | Ship comprehensive defaults. The config.example.yaml already covers ~70 sender/subject patterns across 5 categories. Adding a bank = one line |
| Scheduled background scanning via launchd | "Install once, forget it exists until it saves you" -- the North Star requires zero-touch operation after setup | Medium | Two plists: scan (4h interval, StartInterval: 14400) and digest (weekly Monday 8am). RunAtLoad for immediate first scan on login |
| macOS native notifications | Primary alert surface for the target user. Without this, detections are invisible between terminal sessions | Low | osascript is trivial. Priority-based sounds (Submarine for critical, Pop for high). Batch summary notification when >5 detections |
| Attachment auto-download (PDF, spreadsheet) | Tax docs and statements arrive as attachments. Detection without download is half the value -- users need the file locally | Medium | Multipart MIME traversal, safe filenames (sanitized, no-overwrite with counter suffix), organized by account. Extension filter configurable (.pdf, .xlsx, .xls, .csv, .doc, .docx) |
| Local SQLite storage with audit trail | Privacy is design principle #1. Every detection logged with matched pattern, timestamp, review status. No data leaves the machine | Medium | WAL mode for concurrent read/write. Dedup via UNIQUE(message_id, account_email). Only subject/snippet/sender stored -- no email bodies |
| Interactive review workflow | Users need to track "did I act on this?" -- the CPA/lawyer auditability requirement from VISION.md | Medium | Terminal-based y/n/q/a loop with optional notes. Filter by --category and --account. Bulk --mark-all for catching up |
| Weekly markdown digest | Periodic "nothing slipped through" confirmation. The quarterly save is the product's measure of success | Low | Grouped by category (signature requests first, then tax, equity, brokerage, bank). Summary stats. Unreviewed action items highlighted |
| Quick terminal stats command | "At a glance whether anything needs attention" -- the 5-second check between meetings | Low | Read-only SQLite query. No API calls. Total tracked, unreviewed count, breakdown by category and priority |
| Guided setup (fnsvr init + fnsvr setup) | Without frictionless onboarding, the tool dies at install. Browser-based OAuth like gcloud auth login is the UX bar | High | init creates ~/.fnsvr/ + copies config. setup <account> opens browser OAuth flow, stores token with 600 perms. Clear error messages on missing credentials |
| Read-only Gmail scope (gmail.readonly) | Trust decision, not a limitation. Users with real assets will verify this claim. Anything beyond read-only kills adoption | Low | Architectural constraint enforced at OAuth scope level. Must be prominent in docs, landing page, and README |
| Deduplication | Same email scanned across overlapping lookback windows must not create duplicate entries | Low | UNIQUE constraint on (message_id, account_email). IntegrityError caught silently, returns None for duplicates |
| Error resilience across accounts | One failed account (expired token, rate limit) must not block scanning of other accounts | Medium | Per-account error isolation. Errors collected and stored in scan_log table with status field (running/completed/completed_with_errors) |

## Differentiators

Features that set fnsvr apart from general email tools. Not expected by users who have never seen a tool like this, but create "I didn't know I needed this" moments.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Five-category financial detection taxonomy | No existing tool categorizes emails by financial urgency (tax docs vs. equity vs. banking vs. signatures vs. brokerage). This is fnsvr's domain expertise baked into config defaults | Low | tax_documents (critical), signature_requests (critical), equity_grants (critical), brokerage_statements (high), bank_statements (high). Category display order in digests: most urgent first |
| Priority-based alerting (critical vs. high) | A K1 with a tax deadline and a monthly brokerage statement are not equal. Tiered urgency is how busy execs think about their inbox | Low | Maps to notification sounds and digest ordering. Critical = signature requests, tax docs, equity. High = statements, wires. Different macOS notification sounds per tier |
| Obsidian vault sync for digests | Target users are often Obsidian users (knowledge workers, founders). Auto-syncing digests into their PKM creates a financial paper trail inside their existing workflow | Low | File copy to configured path. Off by default (obsidian_copy: false). One config line to enable. Obsidian email-to-PARA plugin exists but does not cover financial monitoring |
| Matched-pattern audit trail | Every detection records exactly which pattern triggered it (e.g., "subject:k-1" or "sender:docusign"). Forensic-grade transparency that no cloud email tool provides | Low | Already in schema (matched_pattern column). Critical for trust -- users can verify why something was flagged and tune false positives |
| Homebrew formula install | "brew install fnsvr" is the difference between "tool for developers" and "tool for technically comfortable execs." Eliminates Python venv management entirely | Medium | Requires PyPI packaging first, then a Homebrew tap. Formula must handle Python dependency isolation via virtualenv in the cellar |
| Single-file landing page (fnsvr.com) | The website itself is a trust signal -- no tracking, no cookies, no JS frameworks, under 30KB. Mirrors the product's local-first, no-dependency philosophy | Low | Static HTML, inline CSS, dark terminal aesthetic (httpie.io, charm.sh style). GitHub Pages or Vercel deploy. No build step |
| 90-day initial deep scan | First run catches everything already lurking in inboxes. This is the "first run magic moment" -- users immediately see what they have been missing | Low | --initial flag triggers 90-day lookback vs regular 3-day. Custom --days for ad-hoc windows. Surfaces forgotten K1s, unsigned DocuSigns |
| Cross-account unified view | Stats, digest, and review commands aggregate across all accounts. No other tool gives a single pane for financial emails across 3-5 Gmail accounts without being a full email client | Low | SQLite queries span all accounts by default. --account flag for drill-down into a single account |
| launchd auto-configuration | Users should not edit plist XML files. Setup should handle launchctl load/unload automatically | Medium | Copy plists to ~/Library/LaunchAgents/, run launchctl. Must detect correct fnsvr executable path. Needs an uninstall/unschedule path too |

## Anti-Features

Features to explicitly NOT build. Each reason is rooted in the product's design principles from VISION.md.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| GUI or web dashboard | Design principle #4: "Terminal-native." Adding a GUI splits the codebase, doubles maintenance, and dilutes the product identity. Every competitor (Canary Mail, Spark, Mailbird) is a GUI -- fnsvr's differentiation IS the terminal | Keep CLI excellent. Rich terminal output. Stats for quick checks. Digest as markdown viewable in any editor/Obsidian |
| AI/LLM classification | Adds latency, cloud dependency, non-determinism, and cost. Pattern matching is simple, auditable, and fast. Users can read their config and understand exactly what will be detected. SaneBox uses AI and charges $7-36/mo -- fnsvr is free and transparent | Config-driven substring/regex matching. Ship comprehensive defaults. Let users add patterns for their specific institutions. Community-contributed pattern libraries over time |
| Email sending or modification | Read-only is a trust decision. The moment fnsvr can modify emails, it becomes a liability. Target users have real assets and real paranoia about email access | gmail.readonly scope only. Architecturally incapable of modification. Advertise this prominently on landing page and in setup flow |
| Cloud sync or multi-device | Local-first is the point. Cloud sync introduces auth complexity, data residency questions, and a server to maintain. Undermines the core privacy value prop | SQLite on disk. Users can back up ~/.fnsvr/ however they want (Time Machine, iCloud Drive at their discretion). Obsidian sync handles cross-device digest access indirectly |
| Outlook / Microsoft Graph API (v0.1) | Scope creep. The target persona uses Gmail. Adding Outlook doubles the auth surface, API integration work, and testing matrix | Gmail-only for v0.1. Architecture isolates Gmail-specific code (scanner.py) so a future outlook_scanner.py can plug in. Document as community contribution opportunity |
| IMAP support | Gmail API is the right abstraction for this audience. IMAP adds connection management complexity, server compatibility issues, and no advantage for Gmail users | Gmail API provides structured metadata, attachment access, and search without raw IMAP protocol parsing |
| Mobile notifications (push, SMS) | Adds a server component (APNs/FCM or Twilio), which violates local-first. macOS notifications are sufficient for the Mac-based workflow | macOS notifications via osascript. Users wanting mobile alerts can use macOS notification forwarding or Pushover-style bridges at their discretion |
| Encryption at rest for SQLite | Adds complexity (SQLCipher dependency), key management UX burden, and the database only stores subject/snippet/sender -- not email bodies or credentials. The threat model does not justify it for v0.1 | File permissions (600 on tokens, standard user perms on DB). Revisit if users store sensitive content in review notes |
| Full email content storage | Storing email bodies is a privacy liability and storage concern. Subject + snippet + sender is enough for detection, review, and audit | Store only: message_id, subject, sender, date, snippet (500 chars), matched_pattern, review status. Users click through to Gmail for full content |
| Shared OAuth app / auth relay | Would require a server, a Google Cloud project with verified status, and ongoing maintenance. Users authenticating directly with Google is simpler and more trustworthy | Each user creates their own GCP project with gmail.readonly scope. Browser-based OAuth flow like gcloud. Clear setup instructions |
| Real-time push scanning | Gmail API does not support true push to local apps -- push notifications require a Pub/Sub server endpoint. Polling every 4 hours is the right trade-off for a background monitoring tool | launchd 4-hour interval. On-demand "fnsvr scan" for immediate checks. The value is "nothing slips through over days," not "instant alert within seconds" |
| Multi-user / team features | This is a personal tool. Adding user management, sharing, or permissions turns it into enterprise software with entirely different requirements | Single-user, single-machine. MIT license allows anyone to fork for team use cases |

## Feature Dependencies

```
fnsvr init --> config.yaml created
    |
    v
fnsvr setup <account> --> OAuth token stored (requires config with account defined)
    |
    v
fnsvr scan --> detector.py (requires compiled patterns from config)
    |              |
    |              v
    |         storage.py (requires SQLite schema initialized)
    |              |
    |              |---> downloader.py (requires Gmail API service + storage)
    |              |
    |              \---> notifier.py (requires detection results from storage)
    |
    v
fnsvr stats --> storage.py (read-only queries, no API calls)
    |
    v
fnsvr digest --> storage.py + digest.py (read-only queries, markdown file write)
    |                |
    |                \---> Obsidian copy (optional, requires digest file + configured path)
    |
    v
fnsvr review --> storage.py + reviewer.py (read + write for review status/notes)
    |
    v
launchd plists --> fnsvr scan + fnsvr digest (requires working CLI commands)
    |
    v
Homebrew formula --> pyproject.toml + PyPI publish (requires packaged release)
    |
    v
Landing page (fnsvr.com) --> fully independent, can be built in parallel with anything
```

**Critical path:** config.py -> storage.py -> detector.py -> scanner.py -> cli.py (scan command)

**Parallel tracks after core scanning works:**
- Track A: downloader.py + notifier.py (enhance the scan with downloads and alerts)
- Track B: digest.py + reviewer.py + stats (consume stored detections)
- Track C: launchd + Homebrew (distribution and background operation)
- Track D: landing page (marketing, fully independent of code)

## MVP Recommendation

**Phase 1 -- Core Detection Loop (must work before anything else):**
1. Config loading and validation (config.py)
2. SQLite schema and CRUD (storage.py)
3. Pattern matching engine (detector.py) -- pure functions, trivially testable
4. Gmail API scanning (scanner.py) -- auth, message fetch, detection coordination
5. CLI entry point with init, setup, scan commands (cli.py)

**Phase 2 -- User-Facing Value (makes the tool useful day-to-day):**
6. Attachment downloading (downloader.py)
7. macOS notifications (notifier.py)
8. Quick stats command
9. Markdown digest generation (digest.py)
10. Interactive review workflow (reviewer.py)

**Phase 3 -- Distribution and Polish (makes the tool installable and automated):**
11. launchd plist generation and auto-configuration
12. Obsidian vault sync
13. Comprehensive test suite (detector, storage, config, digest)
14. Homebrew formula via tap

**Phase 4 -- Launch (makes the tool discoverable):**
15. Landing page (fnsvr.com)
16. PyPI publishing
17. README and CONTRIBUTING polish

**Defer beyond v0.1:**
- Additional pattern libraries (community contribution path)
- Linux/systemd support (platform module isolation makes this feasible)
- Outlook/Microsoft Graph API
- Rich/Textual for prettier terminal output
- Keychain integration for token storage
- Incremental scanning via Gmail historyId (performance optimization)

**Rationale:** The core value is "scan -> detect -> surface." Everything after that is delivery mechanism (how you see results) and distribution (how you install it). Get the detection loop right first, because if pattern matching produces false positives/negatives or scanning is flaky on token refresh, nothing else matters. Phase 2 makes it useful. Phase 3 makes it automatic. Phase 4 makes it findable.

## Competitive Landscape Summary

There is no direct competitor in this exact niche. The closest tools occupy adjacent spaces:

| Tool | What It Does | Why It Is Not fnsvr |
|------|-------------|-------------------|
| ThunderSweep | Scans Gmail/Drive for sensitive data (SSNs, tax returns) locally in the browser | Browser extension, not CLI. Focused on one-time data cleanup and removal, not ongoing monitoring. Paid ($3.99/mo for continuous Shield monitoring) |
| SaneBox | AI email prioritization across providers via IMAP header analysis | Cloud service (data leaves your machine). General email triage, not financial-specific. No audit trail. $7-36/mo subscription |
| Canary Mail | AI-powered email client with prioritization and triage for executives | Full email client replacement (not additive). Cloud AI processing. Not financial-specific. GUI-only. Subscription pricing |
| Spark / Mailbird | Multi-account unified inbox email clients | Full email clients replacing your workflow. Not financial-specific. Not local-first. GUI-only |
| K1x | AI-powered K-1/1099 extraction and processing | Enterprise tax processing SaaS for CPAs. Not an email scanner. Different audience entirely |
| Gmail filters | Native per-account email rules | Single-account only. No cross-account view. No audit trail. No attachment download. No digest generation |
| Shoeboxed / ExpenseBot | Receipt scanning and expense tracking from Gmail | Focused on receipts/expenses, not financial documents like K1s, equity grants, wire confirmations. Cloud-based |

**fnsvr's unique position:** The only local-first, CLI-based, financial-email-specific, multi-Gmail-account monitoring tool with an audit trail. This is a genuine gap -- every competitor is either cloud-based, GUI-only, general-purpose, or focused on a different financial workflow (tax filing, expense tracking). Nobody is building "quiet background watchdog for the financial emails that matter across all your inboxes."

## Sources

- [ThunderSweep](https://thundersweep.com/) -- closest competitor for local Gmail sensitive data scanning (browser extension, $3.99/mo for monitoring)
- [SaneBox](https://www.sanebox.com/help/155-how-does-sanebox-work) -- AI email prioritization approach, header-only analysis, cloud-based
- [Canary Mail Executive Features](https://canarymail.io/use-cases/inbox-zero-email-app-busy-executives) -- executive email management patterns, AI triage
- [K1x K-1 Aggregator](https://k1x.io/k1-aggregator/) -- financial document processing landscape for K-1/1099
- [Gmail API Scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) -- OAuth scope documentation, gmail.readonly verification
- [Obsidian email-to-PARA plugin](https://github.com/MarkOnFire/obsidian-email-to-para) -- Obsidian email integration ecosystem, auto-sync patterns
- [Himalaya CLI email client](https://github.com/pimalaya/himalaya) -- terminal email tool UX patterns (Rust-based)
- [Mailbird unified inbox guide](https://www.getmailbird.com/managing-multiple-email-accounts-unified-inbox/) -- multi-account email management landscape 2026
- [Briefmatic](https://briefmatic.com/blog/the-best-email-to-task-tools-for-busy-executives-remote-workers) -- executive email-to-task workflow patterns
- [ExpenseBot Gmail Scanner](https://www.expensebot.ai/gmail-receipt-scanner) -- adjacent product: receipt auto-capture from Gmail
