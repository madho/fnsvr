"""Unit tests for fnsvr.config module."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fnsvr.config import (
    ensure_dirs,
    get_config_dir,
    get_config_path,
    init_config,
    load_config,
    resolve_path,
)


class TestGetConfigDir:
    """Tests for get_config_dir()."""

    def test_get_config_dir_default(self, monkeypatch):
        """get_config_dir() returns ~/.fnsvr when FNSVR_CONFIG_DIR is not set."""
        monkeypatch.delenv("FNSVR_CONFIG_DIR", raising=False)
        result = get_config_dir()
        assert result == Path("~/.fnsvr").expanduser()

    def test_config_dir_override(self, monkeypatch, tmp_path):
        """get_config_dir() returns FNSVR_CONFIG_DIR when env var is set."""
        custom_dir = str(tmp_path / "custom-fnsvr")
        monkeypatch.setenv("FNSVR_CONFIG_DIR", custom_dir)
        result = get_config_dir()
        assert result == Path(custom_dir)


class TestGetConfigPath:
    """Tests for get_config_path()."""

    def test_get_config_path(self, monkeypatch, tmp_path):
        """get_config_path() returns get_config_dir() / 'config.yaml'."""
        custom_dir = str(tmp_path / "my-fnsvr")
        monkeypatch.setenv("FNSVR_CONFIG_DIR", custom_dir)
        result = get_config_path()
        assert result == Path(custom_dir) / "config.yaml"


class TestLoadConfig:
    """Tests for load_config()."""

    def test_load_config_valid(self, tmp_path, sample_config):
        """load_config() returns dict with all 4 required keys from valid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(sample_config))
        result = load_config(config_file)
        assert isinstance(result, dict)
        assert set(result.keys()) >= {"accounts", "paths", "categories", "scan"}

    def test_load_config_missing_file(self, tmp_path):
        """load_config() raises FileNotFoundError for nonexistent path."""
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_config(missing)

    def test_load_config_empty_file(self, tmp_path):
        """load_config() raises ValueError with 'YAML mapping' for empty file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ValueError, match="YAML mapping"):
            load_config(empty_file)

    def test_load_config_missing_keys(self, tmp_path):
        """load_config() raises ValueError with 'Missing required config keys' when keys missing."""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(yaml.dump({"paths": {}, "scan": {}}))
        with pytest.raises(ValueError, match="Missing required config keys"):
            load_config(config_file)

    def test_load_config_empty_accounts(self, tmp_path):
        """load_config() raises ValueError when accounts is an empty list."""
        config_file = tmp_path / "empty_accounts.yaml"
        config_data = {
            "accounts": [],
            "paths": {"database": "~/.fnsvr/data/fnsvr.db"},
            "categories": {"tax": {"label": "Tax"}},
            "scan": {"initial_lookback_days": 90},
        }
        config_file.write_text(yaml.dump(config_data))
        with pytest.raises(ValueError, match="'accounts' must be a non-empty list"):
            load_config(config_file)


class TestResolvePath:
    """Tests for resolve_path()."""

    def test_resolve_path_tilde(self):
        """resolve_path('~/foo') returns Path.home() / 'foo'."""
        result = resolve_path("~/foo")
        assert result == Path.home() / "foo"

    def test_resolve_path_env_var(self, monkeypatch):
        """resolve_path('$HOME/foo') expands $HOME correctly."""
        monkeypatch.setenv("HOME", "/Users/testuser")
        result = resolve_path("$HOME/foo")
        assert result == Path("/Users/testuser/foo")


class TestEnsureDirs:
    """Tests for ensure_dirs()."""

    def test_ensure_dirs(self, tmp_path):
        """ensure_dirs() creates all 4 directories from config.paths."""
        config = {
            "paths": {
                "database": str(tmp_path / "data" / "fnsvr.db"),
                "attachments": str(tmp_path / "data" / "attachments"),
                "digests": str(tmp_path / "data" / "digests"),
                "logs": str(tmp_path / "data" / "logs"),
            }
        }
        ensure_dirs(config)
        assert (tmp_path / "data" / "fnsvr.db").is_dir()
        assert (tmp_path / "data" / "attachments").is_dir()
        assert (tmp_path / "data" / "digests").is_dir()
        assert (tmp_path / "data" / "logs").is_dir()


class TestInitConfig:
    """Tests for init_config()."""

    def test_init_config_creates_dir(self, monkeypatch, tmp_path):
        """init_config() creates the config dir and copies config.example.yaml."""
        config_dir = tmp_path / "fnsvr-init"
        monkeypatch.setenv("FNSVR_CONFIG_DIR", str(config_dir))
        result = init_config()
        assert config_dir.is_dir()
        assert result.exists()
        assert result.name == "config.yaml"
        # Verify content contains categories (from the example config)
        content = result.read_text()
        assert "categories" in content

    def test_init_config_existing_no_force(self, monkeypatch, tmp_path):
        """init_config() raises FileExistsError when config already exists."""
        config_dir = tmp_path / "fnsvr-exists"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("existing: true")
        monkeypatch.setenv("FNSVR_CONFIG_DIR", str(config_dir))
        with pytest.raises(FileExistsError):
            init_config()

    def test_init_config_force(self, monkeypatch, tmp_path):
        """init_config(force=True) overwrites existing config."""
        config_dir = tmp_path / "fnsvr-force"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("old: true")
        monkeypatch.setenv("FNSVR_CONFIG_DIR", str(config_dir))
        result = init_config(force=True)
        content = result.read_text()
        assert "old" not in content
        assert "categories" in content
