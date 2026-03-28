# Contributing to fnsvr

Thanks for your interest. Here's how to get started.

## Development Setup

```bash
git clone https://github.com/madho/fnsvr.git
cd fnsvr
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest -v
pytest --cov=fnsvr
```

## Code Style

We use [ruff](https://docs.astral.sh/ruff/):

```bash
ruff check src/ tests/
ruff format src/ tests/
```

Conventions: type hints on all function signatures, docstrings on all public functions, minimal dependencies, no ORM.

## Most Valuable Contributions

1. **Detection patterns.** More banks, brokers, e-signature platforms, international financial institutions. Edit `config.example.yaml` and add a test case.
2. **Platform support.** Linux notifications, systemd timers, Windows Task Scheduler.
3. **Additional email providers.** Outlook/Microsoft Graph API, IMAP.
4. **Tests.** Especially for edge cases in pattern matching and config validation.

## Pull Requests

- One feature or fix per PR
- Include tests for new functionality
- Update CLAUDE.md if architecture or commands change
- Keep PRs focused

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
