"""Configuration loading, validation, path resolution, and initialization."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import yaml

_DEFAULT_CONFIG_DIR = "~/.fnsvr"
_ENV_VAR = "FNSVR_CONFIG_DIR"


def get_config_dir() -> Path:
    """Return ~/.fnsvr or FNSVR_CONFIG_DIR env override."""
    env_dir = os.environ.get(_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser()
    return Path(_DEFAULT_CONFIG_DIR).expanduser()


def get_config_path() -> Path:
    """Return path to active config.yaml."""
    return get_config_dir() / "config.yaml"


def load_config(config_path: Path | None = None) -> dict:
    """Load, validate, return config dict.

    Raises:
        FileNotFoundError: If config file does not exist.
        ValueError: If config is not valid YAML or missing required keys.
    """
    if config_path is None:
        config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Config must be a YAML mapping, got {type(config).__name__}")
    required_keys = {"accounts", "paths", "categories", "scan"}
    missing = required_keys - config.keys()
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(sorted(missing))}")
    if not config.get("accounts") or not isinstance(config["accounts"], list):
        raise ValueError("'accounts' must be a non-empty list")
    return config


def resolve_path(path_str: str) -> Path:
    """Expand ~ and $ENV_VARS in path strings."""
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def ensure_dirs(config: dict) -> None:
    """Create all data directories from config.paths."""
    for _key, path_str in config["paths"].items():
        resolved = resolve_path(path_str)
        resolved.mkdir(parents=True, exist_ok=True)


def init_config(force: bool = False) -> Path:
    """Create config dir and copy config.example.yaml.

    Returns:
        Path to the new config file.

    Raises:
        FileExistsError: If config already exists and force is False.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    dest = config_dir / "config.yaml"
    if dest.exists() and not force:
        raise FileExistsError(f"Config already exists: {dest}")
    # Find bundled config.example.yaml
    source = Path(__file__).parent / "config.example.yaml"
    shutil.copy2(source, dest)
    return dest
