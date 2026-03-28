"""Click CLI entry point for fnsvr."""
from __future__ import annotations

import logging
import sys

import click

from fnsvr import config, scanner, storage


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def main(verbose: bool) -> None:
    """fnsvr -- Financial inbox monitor for Gmail."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@main.command()
@click.option("--force", is_flag=True, help="Overwrite existing config.")
def init(force: bool) -> None:
    """Create ~/.fnsvr/ directory and copy example config."""
    try:
        path = config.init_config(force=force)
        click.echo(f"Config created: {path}")
        click.echo("Edit this file, then run: fnsvr setup <account_name>")
    except FileExistsError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)


@main.command()
@click.argument("account_name")
def setup(account_name: str) -> None:
    """Run OAuth flow for a Gmail account.

    ACCOUNT_NAME must match a name in your config.yaml accounts list.
    """
    try:
        cfg = config.load_config()
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    config_dir = config.get_config_dir()
    account = None
    for acct in cfg["accounts"]:
        if acct["name"] == account_name:
            account = acct
            break

    if account is None:
        names = ", ".join(a["name"] for a in cfg["accounts"])
        click.echo(
            f"Account '{account_name}' not found in config. Available: {names}",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Starting OAuth flow for '{account_name}'...")
    click.echo("A browser window will open. Sign in and grant read-only access.")
    try:
        scanner.setup_oauth(account, config_dir)
        click.echo(f"Authentication complete for '{account_name}'. Token saved.")
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"OAuth setup failed: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option("--initial", is_flag=True, help="Deep scan with 90-day lookback.")
@click.option("--days", type=int, default=None, help="Custom lookback in days.")
@click.option(
    "--account", "account_name", default=None, help="Scan single account by name."
)
def scan(initial: bool, days: int | None, account_name: str | None) -> None:
    """Scan Gmail accounts for financial emails."""
    try:
        cfg = config.load_config()
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    config.ensure_dirs(cfg)
    config_dir = config.get_config_dir()
    db_path = config.resolve_path(cfg["paths"]["database"])
    conn = storage.init_db(db_path)

    # Determine lookback days (per SCAN-01, SCAN-02, SCAN-03)
    if days is not None:
        lookback = days
    elif initial:
        lookback = cfg["scan"].get("initial_lookback_days", 90)
    else:
        lookback = cfg["scan"].get("regular_lookback_days", 3)

    click.echo(f"Scanning with {lookback}-day lookback...")

    try:
        results = scanner.scan_all(
            cfg, conn, lookback, config_dir, account_filter=account_name
        )
    finally:
        conn.close()

    # Display results
    for name, scanned, detected, downloaded, error in results:
        if error:
            click.echo(f"  {name}: ERROR - {error}", err=True)
        else:
            click.echo(
                f"  {name}: scanned={scanned}, detected={detected}, "
                f"downloaded={downloaded}"
            )

    total_detected = sum(r[2] for r in results)
    total_errors = sum(1 for r in results if r[4])
    if total_errors:
        click.echo(
            f"\n{total_errors} account(s) had errors. Run with -v for details."
        )
    click.echo(f"Total detections: {total_detected}")
