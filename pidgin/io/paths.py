"""Path utilities for consistent output directory handling."""

import os
from pathlib import Path

from .logger import get_logger

logger = get_logger("paths")

# Default output directory name
DEFAULT_OUTPUT_DIR = "pidgin_output"


def get_output_dir() -> Path:
    """Get the base output directory, resolving from the original working directory.

    Returns:
        Path to output directory in user's current working directory
    """
    # Priority order for determining the working directory:
    # 1. PIDGIN_ORIGINAL_CWD (set at CLI startup)
    # 2. PWD (shell's current directory)
    # 3. os.getcwd() (process's current directory)

    original_cwd = os.environ.get("PIDGIN_ORIGINAL_CWD")
    if original_cwd and os.path.exists(original_cwd):
        base_path = Path(original_cwd)
    else:
        # Try PWD which is more reliable for shell working directory
        pwd = os.environ.get("PWD")
        if pwd and os.path.exists(pwd):
            base_path = Path(pwd)
        else:
            # Final fallback
            base_path = Path(os.getcwd())

    # Check if we're running from the pidgin source directory during development
    # If there's a pidgin/ subdirectory with __init__.py, we're in the dev directory
    if (base_path / "pidgin" / "__init__.py").exists() and (
        base_path / "pyproject.toml"
    ).exists():
        # We're in the development directory, use a different output name
        output_dir = base_path / "pidgin_dev_output"
    else:
        # Normal usage - use the standard output directory name
        output_dir = base_path / DEFAULT_OUTPUT_DIR

    # Debug logging (only if PIDGIN_DEBUG is set)
    if os.environ.get("PIDGIN_DEBUG"):
        print(f"[DEBUG] Output directory: {output_dir}")
        print(f"[DEBUG] PIDGIN_ORIGINAL_CWD: {os.environ.get('PIDGIN_ORIGINAL_CWD')}")
        print(f"[DEBUG] PWD: {os.environ.get('PWD')}")
        print(f"[DEBUG] os.getcwd(): {os.getcwd()}")

    return output_dir


def get_experiments_dir() -> Path:
    """Get the experiments output directory.

    Returns:
        Path to pidgin/experiments directory
    """
    return get_output_dir() / "experiments"


def get_conversations_dir() -> Path:
    """Get the conversations output directory.

    Returns:
        Path to pidgin/conversations directory
    """
    return get_output_dir() / "conversations"


def get_database_path() -> Path:
    """Get the path to the experiments database.

    Returns:
        Path to pidgin/experiments.duckdb
    """
    return get_output_dir() / "experiments.duckdb"
