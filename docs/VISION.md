# fnsvr -- Vision

## The Problem

Financial emails get buried. A K1 from a partnership arrives in March and sits unnoticed until your CPA asks for it in April. A DocuSign for an equity agreement expires because it landed between a newsletter and a promo blast. A wire confirmation from your bank gets lost in a sea of alerts you've trained yourself to ignore.

This isn't a notification problem. It's a signal-to-noise problem across multiple inboxes. People with complex financial lives -- founders, investors, freelancers, anyone with multiple income streams or business entities -- are spread across 3+ email accounts. The financial emails that actually matter represent maybe 0.1% of their total volume. And unlike a missed meeting invite, a missed K1 or unsigned equity doc has real financial and legal consequences.

Gmail's native filters help, but they don't work across accounts, they can't prioritize by financial urgency, and they don't create an auditable trail of what arrived and whether you acted on it.

## The Solution

fnsvr is a local watchdog for your inboxes. It connects to your Gmail accounts (read-only), scans for financial emails using configurable pattern matching, and makes sure nothing important slips through. It runs quietly on your Mac via launchd, stores everything locally in SQLite, and surfaces what matters through macOS notifications, terminal-friendly digests, and an interactive review workflow.

**It does not:**
- Touch, modify, or delete your emails
- Send any data to external services
- Require a server, cloud account, or subscription
- Try to be an email client

**It does:**
- Scan 3+ Gmail accounts on a 4-hour cycle
- Detect K1s, 1099s, investment statements, wire confirmations, equity grants, and signature requests
- Auto-download PDF and spreadsheet attachments
- Send macOS notifications with priority-based alerting
- Generate weekly markdown digests (with optional Obsidian sync)
- Track review status so you know what you've acted on and what's still pending

## Who Is This For?

**Primary persona:** Someone with a complex financial life and multiple Gmail accounts. Founders, investors, freelancers, people with side businesses or partnership interests. They're technically comfortable (can run a Python install) but don't want to maintain infrastructure.

**Secondary persona:** Open source contributors who want to extend the pattern library for their own financial institutions, or build on the architecture for other email-monitoring use cases.

## Design Principles

1. **Local-first, always.** No cloud. No SaaS. No accounts to create. Your email data never leaves your machine. This is non-negotiable.

2. **Read-only by design.** The Gmail API scope is gmail.readonly. The app is architecturally incapable of modifying your email. This is a trust decision -- users should never worry about what fnsvr might do to their inbox.

3. **Config over code.** Adding a new bank, broker, or e-signature provider should be a one-line YAML edit, not a pull request. The pattern engine is intentionally simple (substring matching) because it needs to be maintainable by non-developers.

4. **Terminal-native.** This is a CLI tool. No GUI, no web dashboard, no Electron. It should feel at home next to `git`, `brew`, and `htop`. Power users live in the terminal; meet them there.

5. **Quiet until it matters.** The default mode is silent background scanning. When something financial shows up, it should surface clearly -- a macOS notification, a digest entry, a review queue item -- and then get out of the way.

6. **Auditable.** Every scan is logged. Every detection is recorded with the pattern that matched. Every review action is timestamped. If you need to prove to your CPA or lawyer that you saw (or didn't see) something, the data is there.

## North Star

fnsvr should be the kind of tool where you install it once, configure it in 10 minutes, and then forget it exists -- until it saves you from missing something that would have cost you real money. The measure of success is not daily active usage. It's the one time per quarter it catches something you would have missed.

## Open Source Strategy

fnsvr is MIT-licensed and designed to be extended. The most valuable community contributions will be:

- **Pattern libraries.** More banks, more brokers, more e-signature platforms, international financial institutions. The config.example.yaml should grow into a comprehensive reference.
- **Platform support.** Linux notification support, systemd timers as a launchd alternative, Windows Task Scheduler.
- **Additional email providers.** Outlook/Microsoft Graph API, IMAP support for self-hosted email.
- **Reporting.** Tax-season readiness reports, annual summaries, integration with personal finance tools.

The core scanning and detection logic should stay simple and stable. Complexity should live at the edges -- more patterns, more platforms, more output formats.
