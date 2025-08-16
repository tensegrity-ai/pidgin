"""XDG Base Directory support for Pidgin.

This module provides functions to get appropriate directories following
the XDG Base Directory specification, with automatic directory creation.
"""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Get the configuration directory for Pidgin.

    Returns ~/.config/pidgin/ by default, or respects $XDG_CONFIG_HOME if set.
    Creates the directory if it doesn't exist.

    Returns:
        Path to the configuration directory
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "pidgin"
    else:
        config_dir = Path.home() / ".config" / "pidgin"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_cache_dir() -> Path:
    """Get the cache directory for Pidgin.

    Returns ~/.cache/pidgin/ by default, or respects $XDG_CACHE_HOME if set.
    Creates the directory if it doesn't exist.

    Returns:
        Path to the cache directory
    """
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        cache_dir = Path(xdg_cache_home) / "pidgin"
    else:
        cache_dir = Path.home() / ".cache" / "pidgin"

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_data_dir() -> Path:
    """Get the data directory for Pidgin.

    Returns ~/.local/share/pidgin/ by default, or respects $XDG_DATA_HOME if set.
    Creates the directory if it doesn't exist.

    Returns:
        Path to the data directory
    """
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        data_dir = Path(xdg_data_home) / "pidgin"
    else:
        data_dir = Path.home() / ".local" / "share" / "pidgin"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_default_output_dir() -> Path:
    """Get the default output directory for experiments.

    Returns ./pidgin/ in the current working directory.
    Does NOT create the directory automatically.

    Returns:
        Path to the default output directory
    """
    return Path.cwd() / "pidgin"
