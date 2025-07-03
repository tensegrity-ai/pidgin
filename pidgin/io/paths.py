"""Path utilities for consistent output directory handling."""

import os
from pathlib import Path


def get_output_dir() -> Path:
    """Get the base output directory, resolving from the original working directory.
    
    Returns:
        Path to pidgin_output directory
    """
    # Try to get from environment (set during CLI initialization)
    original_cwd = os.environ.get('PIDGIN_ORIGINAL_CWD')
    
    # Fall back to PWD or current directory
    if not original_cwd:
        original_cwd = os.environ.get('PWD', os.getcwd())
    
    return Path(original_cwd) / "pidgin_output"


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