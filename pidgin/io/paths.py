"""Path utilities for consistent output directory handling."""

import os
from pathlib import Path


def get_output_dir() -> Path:
    """Get the base output directory, resolving from the original working directory.
    
    Returns:
        Path to pidgin_output directory in user's current working directory
    """
    # Priority order for determining the working directory:
    # 1. PIDGIN_ORIGINAL_CWD (set at CLI startup)
    # 2. PWD (shell's current directory)
    # 3. os.getcwd() (process's current directory)
    
    original_cwd = os.environ.get('PIDGIN_ORIGINAL_CWD')
    if original_cwd and os.path.exists(original_cwd):
        base_path = Path(original_cwd)
    else:
        # Try PWD which is more reliable for shell working directory
        pwd = os.environ.get('PWD')
        if pwd and os.path.exists(pwd):
            base_path = Path(pwd)
        else:
            # Final fallback
            base_path = Path(os.getcwd())
    
    output_dir = base_path / "pidgin_output"
    
    # Debug logging (only if PIDGIN_DEBUG is set)
    if os.environ.get('PIDGIN_DEBUG'):
        print(f"[DEBUG] Output directory: {output_dir}")
        print(f"[DEBUG] PIDGIN_ORIGINAL_CWD: {os.environ.get('PIDGIN_ORIGINAL_CWD')}")
        print(f"[DEBUG] PWD: {os.environ.get('PWD')}")
        print(f"[DEBUG] os.getcwd(): {os.getcwd()}")
    
    return output_dir


def get_experiments_dir() -> Path:
    """Get the experiments output directory.
    
    Returns:
        Path to pidgin_output/experiments directory
    """
    return get_output_dir() / "experiments"


def get_conversations_dir() -> Path:
    """Get the conversations output directory.
    
    Returns:
        Path to pidgin_output/conversations directory
    """
    return get_output_dir() / "conversations"


def get_database_path() -> Path:
    """Get the path to the experiments database.
    
    Returns:
        Path to experiments.duckdb
    """
    return get_experiments_dir() / "experiments.duckdb"


def get_chats_database_path() -> Path:
    """Get the path to the chats database.
    
    Returns:
        Path to chats.duckdb in user's home .pidgin directory
    """
    return Path.home() / ".pidgin" / "chats.duckdb"