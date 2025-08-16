"""File I/O utilities for consistent JSON handling and atomic operations."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def safe_json_load(file_path: Path, default: Optional[Any] = None) -> Any:
    """Safely load JSON from a file with error handling.

    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or has errors

    Returns:
        Loaded JSON data or default value
    """
    try:
        with open(file_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default if default is not None else {}


def atomic_json_write(file_path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """Atomically write JSON data to a file using temporary file and replace.

    Args:
        file_path: Target file path
        data: Data to write as JSON
        indent: JSON indentation level
    """
    temp_path = file_path.with_suffix(".tmp")

    try:
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=indent)

        # Atomic replace operation
        os.replace(temp_path, file_path)
    except Exception:
        # Clean up temp file if something went wrong
        if temp_path.exists():
            temp_path.unlink()
        raise


def safe_mkdir(path: Path) -> None:
    """Safely create directory with parents, ignoring if it already exists.

    Args:
        path: Directory path to create
    """
    path.mkdir(parents=True, exist_ok=True)
