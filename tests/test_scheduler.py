"""Tests for fnsvr.scheduler -- plist generation and path detection."""
from __future__ import annotations

import plistlib
from pathlib import Path
from unittest.mock import patch

from fnsvr import scheduler


def test_scan_plist_contains_correct_interval() -> None:
    """Scan plist has StartInterval 14400 and RunAtLoad true."""
    xml = scheduler.generate_scan_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    plist = plistlib.loads(xml.encode("utf-8"))
    assert plist["StartInterval"] == 14400
    assert plist["RunAtLoad"] is True


def test_digest_plist_contains_calendar_interval() -> None:
    """Digest plist has StartCalendarInterval with Weekday=1, Hour=8, Minute=0."""
    xml = scheduler.generate_digest_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    plist = plistlib.loads(xml.encode("utf-8"))
    cal = plist["StartCalendarInterval"]
    assert cal["Weekday"] == 1
    assert cal["Hour"] == 8
    assert cal["Minute"] == 0


def test_plist_has_absolute_binary_path() -> None:
    """ProgramArguments[0] is an absolute path (starts with /)."""
    xml = scheduler.generate_scan_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    plist = plistlib.loads(xml.encode("utf-8"))
    assert plist["ProgramArguments"][0].startswith("/")


def test_plist_has_log_paths() -> None:
    """StandardOutPath and StandardErrorPath point to log dir."""
    log_dir = Path("/Users/test/.fnsvr/data/logs")
    xml = scheduler.generate_scan_plist("/usr/local/bin/fnsvr", log_dir)
    plist = plistlib.loads(xml.encode("utf-8"))
    assert plist["StandardOutPath"] == str(log_dir / "scan.log")
    assert plist["StandardErrorPath"] == str(log_dir / "scan-error.log")


def test_plist_label_correct() -> None:
    """Scan plist Label is com.fnsvr.scan, digest is com.fnsvr.digest."""
    scan_xml = scheduler.generate_scan_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    digest_xml = scheduler.generate_digest_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    scan_plist = plistlib.loads(scan_xml.encode("utf-8"))
    digest_plist = plistlib.loads(digest_xml.encode("utf-8"))
    assert scan_plist["Label"] == "com.fnsvr.scan"
    assert digest_plist["Label"] == "com.fnsvr.digest"


def test_find_fnsvr_binary_returns_absolute_path() -> None:
    """_find_fnsvr_binary returns an absolute path string."""
    with patch("shutil.which", return_value="/usr/local/bin/fnsvr"):
        result = scheduler._find_fnsvr_binary()
    assert result.startswith("/")


def test_digest_plist_log_paths() -> None:
    """Digest plist has correct log paths."""
    log_dir = Path("/Users/test/.fnsvr/data/logs")
    xml = scheduler.generate_digest_plist("/usr/local/bin/fnsvr", log_dir)
    plist = plistlib.loads(xml.encode("utf-8"))
    assert plist["StandardOutPath"] == str(log_dir / "digest.log")
    assert plist["StandardErrorPath"] == str(log_dir / "digest-error.log")


def test_scan_plist_program_arguments() -> None:
    """Scan plist ProgramArguments is [binary, 'scan']."""
    xml = scheduler.generate_scan_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    plist = plistlib.loads(xml.encode("utf-8"))
    assert plist["ProgramArguments"] == ["/usr/local/bin/fnsvr", "scan"]


def test_digest_plist_program_arguments() -> None:
    """Digest plist ProgramArguments is [binary, 'digest']."""
    xml = scheduler.generate_digest_plist("/usr/local/bin/fnsvr", Path("/tmp/logs"))
    plist = plistlib.loads(xml.encode("utf-8"))
    assert plist["ProgramArguments"] == ["/usr/local/bin/fnsvr", "digest"]
