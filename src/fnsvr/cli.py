"""Click CLI entry point for fnsvr."""
from __future__ import annotations

import logging
import sys

import click

from fnsvr import config, reviewer, scanner, scheduler, storage
from fnsvr import digest as digest_module


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


@main.command()
@click.option("--days", type=int, default=7, help="Lookback period in days.")
@click.option("--unreviewed", is_flag=True, help="Show only unreviewed items.")
@click.option("--no-save", is_flag=True, help="Print to stdout without saving.")
def digest(days: int, unreviewed: bool, no_save: bool) -> None:
    """Generate a markdown digest of recent detections."""
    try:
        cfg = config.load_config()
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    config.ensure_dirs(cfg)
    db_path = config.resolve_path(cfg["paths"]["database"])
    conn = storage.init_db(db_path)

    try:
        rows = storage.get_emails_by_date_range(
            conn, days=days, unreviewed_only=unreviewed
        )
        emails = [dict(row) for row in rows]
        content = digest_module.generate_digest(
            emails, title=f"fnsvr Digest -- Last {days} Days"
        )

        if no_save:
            click.echo(content)
            return

        path = digest_module.save_digest(content, cfg, no_save=no_save)
        if path:
            click.echo(f"Digest saved: {path}")
        click.echo(content)
    finally:
        conn.close()


@main.command()
@click.option("--category", default=None, help="Filter by category.")
@click.option("--account", default=None, help="Filter by account name.")
@click.option(
    "--mark-all", "mark_all_flag", is_flag=True,
    help="Mark all unreviewed as reviewed.",
)
def review(
    category: str | None, account: str | None, mark_all_flag: bool
) -> None:
    """Interactively review unreviewed detections."""
    try:
        cfg = config.load_config()
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    db_path = config.resolve_path(cfg["paths"]["database"])
    conn = storage.init_db(db_path)

    try:
        emails = storage.get_unreviewed(conn, category=category, account=account)
        if not emails:
            click.echo("No unreviewed items.")
            return

        if mark_all_flag:
            count = reviewer.mark_all(conn, emails)
            click.echo(f"Marked {count} item(s) as reviewed.")
        else:
            reviewer.review_interactive(conn, emails)
    finally:
        conn.close()


@main.command()
def stats() -> None:
    """Show summary statistics from local database."""
    try:
        cfg = config.load_config()
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    db_path = config.resolve_path(cfg["paths"]["database"])
    conn = storage.init_db(db_path)

    try:
        data = storage.get_stats(conn)
        click.echo("fnsvr Stats")
        click.echo("-----------")
        click.echo(f"Total tracked:  {data['total']}")
        click.echo(f"Unreviewed:     {data['unreviewed']}")
        click.echo("")

        click.echo("By Category:")
        if data["by_category"]:
            for cat, count in sorted(data["by_category"].items()):
                click.echo(f"  {cat}: {count}")
        else:
            click.echo("  (none)")
        click.echo("")

        click.echo("By Priority:")
        if data["by_priority"]:
            for priority, count in sorted(data["by_priority"].items()):
                click.echo(f"  {priority}: {count}")
        else:
            click.echo("  (none)")
    finally:
        conn.close()


@main.group()
def schedule() -> None:
    """Manage launchd scheduling for automated scanning and digests."""


@schedule.command()
def install() -> None:
    """Install launchd plists for automatic scanning and digest generation."""
    try:
        scan_path, digest_path = scheduler.install_schedule()
        click.echo(f"Scan plist installed:   {scan_path}")
        click.echo(f"Digest plist installed: {digest_path}")
        click.echo("Scanning every 4 hours. Weekly digest on Mondays at 8am.")
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Install failed: {exc}", err=True)
        sys.exit(1)


@schedule.command()
def uninstall() -> None:
    """Uninstall launchd plists and stop automated scheduling."""
    scan_removed, digest_removed = scheduler.uninstall_schedule()
    if scan_removed:
        click.echo("Scan plist removed.")
    else:
        click.echo("Scan plist was not installed.")
    if digest_removed:
        click.echo("Digest plist removed.")
    else:
        click.echo("Digest plist was not installed.")
    click.echo("Scheduling disabled.")


@schedule.command()
def status() -> None:
    """Show current launchd scheduling state."""
    state = scheduler.schedule_status()
    for name in ("scan", "digest"):
        info = state[name]
        if info["installed"]:
            click.echo(f"{name}: installed ({info['plist_path']})")
        else:
            click.echo(f"{name}: not installed")
