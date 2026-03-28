# fnsvr

Local-first Gmail scanner that catches financial emails you can't afford to miss.

Monitors multiple Gmail accounts for K1s, 1099s, investment statements, bank wires, equity grants, and signature requests. Runs on your Mac, stores everything locally, notifies you when something important arrives.

## Status

**v0.1 -- In Development**

## Quick Start

```bash
git clone https://github.com/madho/fnsvr.git
cd fnsvr
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

fnsvr init                    # Create config
# Edit ~/.fnsvr/config.yaml with your Gmail accounts
fnsvr setup personal          # OAuth for each account
fnsvr scan --initial          # First scan (90 days back)
```

## What It Does

- Scans 3+ Gmail accounts on a 4-hour schedule (via launchd)
- Detects financial emails using configurable pattern matching
- Auto-downloads PDF and spreadsheet attachments
- Sends macOS notifications with priority-based alerting
- Generates weekly markdown digests (optional Obsidian sync)
- Tracks review status so nothing slips through

## What It Doesn't Do

- Modify, delete, or send emails (read-only Gmail access)
- Send data to external services (everything stays on your machine)
- Require a server, cloud account, or subscription

## Documentation

- [Vision](docs/VISION.md) -- Why this exists and design principles
- [Product Requirements](docs/PRD.md) -- Features and acceptance criteria
- [Technical Spec](docs/TECH_SPEC.md) -- Architecture and data model
- [Contributing](CONTRIBUTING.md) -- How to help

## License

MIT
