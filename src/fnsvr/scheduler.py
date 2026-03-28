"""launchd scheduling for fnsvr -- plist generation, install, uninstall, status."""
from __future__ import annotations

import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from fnsvr.config import get_config_dir

SCAN_LABEL = "com.fnsvr.scan"
DIGEST_LABEL = "com.fnsvr.digest"
SCAN_PLIST_NAME = f"{SCAN_LABEL}.plist"
DIGEST_PLIST_NAME = f"{DIGEST_LABEL}.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def _find_fnsvr_binary() -> str:
    """Detect the absolute path to the fnsvr executable.

    Strategy: shutil.which first, then sys.executable sibling, then python -m fallback.
    """
    which_result = shutil.which("fnsvr")
    if which_result is not None:
        return str(Path(which_result).resolve())

    sibling = Path(sys.executable).parent / "fnsvr"
    if sibling.exists():
        return str(sibling.resolve())

    # Fallback: use the Python interpreter to run fnsvr as a module
    return str(Path(sys.executable).resolve())


def _fnsvr_program_arguments(binary_path: str, subcommand: str) -> list[str]:
    """Build ProgramArguments list for a plist.

    If binary_path equals sys.executable (module fallback), use [python, -m, fnsvr, cmd].
    Otherwise use [binary, cmd].
    """
    resolved_exe = str(Path(sys.executable).resolve())
    if binary_path == resolved_exe:
        return [binary_path, "-m", "fnsvr", subcommand]
    return [binary_path, subcommand]


def generate_scan_plist(binary_path: str, log_dir: Path) -> str:
    """Return XML string for com.fnsvr.scan.plist.

    StartInterval = 14400 (4 hours). RunAtLoad = true.
    """
    plist_dict: dict = {
        "Label": SCAN_LABEL,
        "ProgramArguments": _fnsvr_program_arguments(binary_path, "scan"),
        "StartInterval": 14400,
        "RunAtLoad": True,
        "WorkingDirectory": str(Path.home()),
        "StandardOutPath": str(log_dir / "scan.log"),
        "StandardErrorPath": str(log_dir / "scan-error.log"),
    }
    return plistlib.dumps(plist_dict, fmt=plistlib.FMT_XML).decode("utf-8")


def generate_digest_plist(binary_path: str, log_dir: Path) -> str:
    """Return XML string for com.fnsvr.digest.plist.

    StartCalendarInterval: Monday at 8:00 AM.
    """
    plist_dict: dict = {
        "Label": DIGEST_LABEL,
        "ProgramArguments": _fnsvr_program_arguments(binary_path, "digest"),
        "StartCalendarInterval": {
            "Weekday": 1,
            "Hour": 8,
            "Minute": 0,
        },
        "WorkingDirectory": str(Path.home()),
        "StandardOutPath": str(log_dir / "digest.log"),
        "StandardErrorPath": str(log_dir / "digest-error.log"),
    }
    return plistlib.dumps(plist_dict, fmt=plistlib.FMT_XML).decode("utf-8")


def install_schedule(log_dir: Path | None = None) -> tuple[Path, Path]:
    """Install both launchd plists and load them.

    Returns tuple of (scan_plist_path, digest_plist_path).
    Raises RuntimeError if not macOS.
    """
    if platform.system() != "Darwin":
        raise RuntimeError("launchd scheduling is only available on macOS")

    binary_path = _find_fnsvr_binary()
    if log_dir is None:
        log_dir = get_config_dir() / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    scan_plist = LAUNCH_AGENTS_DIR / SCAN_PLIST_NAME
    digest_plist = LAUNCH_AGENTS_DIR / DIGEST_PLIST_NAME

    scan_plist.write_text(generate_scan_plist(binary_path, log_dir))
    digest_plist.write_text(generate_digest_plist(binary_path, log_dir))

    subprocess.run(["launchctl", "load", str(scan_plist)], check=True)
    subprocess.run(["launchctl", "load", str(digest_plist)], check=True)

    return scan_plist, digest_plist


def uninstall_schedule() -> tuple[bool, bool]:
    """Unload and remove both launchd plists.

    Returns (scan_removed, digest_removed). Does not error if files missing.
    """
    scan_removed = _unload_and_remove(LAUNCH_AGENTS_DIR / SCAN_PLIST_NAME)
    digest_removed = _unload_and_remove(LAUNCH_AGENTS_DIR / DIGEST_PLIST_NAME)
    return scan_removed, digest_removed


def _unload_and_remove(plist_path: Path) -> bool:
    """Unload a plist via launchctl and delete the file."""
    if not plist_path.exists():
        return False
    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        check=False,
        capture_output=True,
    )
    plist_path.unlink()
    return True


def schedule_status() -> dict:
    """Check current scheduling state.

    Returns dict with keys 'scan' and 'digest', each having
    'installed' (bool) and 'plist_path' (str | None).
    """
    result: dict = {}
    for name, plist_name in [("scan", SCAN_PLIST_NAME), ("digest", DIGEST_PLIST_NAME)]:
        plist_path = LAUNCH_AGENTS_DIR / plist_name
        if plist_path.exists():
            result[name] = {
                "installed": True,
                "plist_path": str(plist_path),
            }
        else:
            result[name] = {
                "installed": False,
                "plist_path": None,
            }
    return result
