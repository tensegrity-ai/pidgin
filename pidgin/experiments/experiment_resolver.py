"""Resolve experiment identifiers to IDs and directories."""

import json
import logging
from pathlib import Path
from typing import Optional


class ExperimentResolver:
    """Handles experiment ID resolution and discovery."""

    def __init__(self, base_dir: Path):
        """Initialize resolver.

        Args:
            base_dir: Base directory for experiments
        """
        self.base_dir = base_dir

    def find_experiment_by_name(self, name: str) -> Optional[str]:
        """Find experiment ID by name.

        Args:
            name: Experiment name to search for

        Returns:
            Experiment ID if found, None otherwise
        """
        # Search all directories, not just those starting with "experiment_"
        for experiment_dir in self.base_dir.iterdir():
            if not experiment_dir.is_dir() or experiment_dir.name in ["active", "logs"]:
                continue

            # Check manifest for name
            manifest_path = experiment_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        if manifest.get("name") == name:
                            return manifest.get("experiment_id")
                except (json.JSONDecodeError, OSError):
                    # Manifest might be corrupted or inaccessible
                    pass

            # Check if the name is in the directory name itself
            # Format: name_shortid (e.g., "curious-echo_a1b2c3d4")
            if "_" in experiment_dir.name:
                parts = experiment_dir.name.rsplit("_", 1)  # Split from the right
                if len(parts) == 2:
                    dir_name = parts[0]
                    short_id = parts[1]
                    # Compare with sanitized input name
                    if dir_name == name.replace(" ", "-").replace("/", "-")[:30]:
                        return f"experiment_{short_id}"

        return None

    def resolve_experiment_id(self, identifier: str) -> Optional[str]:
        """Resolve an experiment identifier to a full experiment ID.

        Supports:
        - Full experiment ID: experiment_a1b2c3d4
        - Shortened ID: a1b2c3d4
        - Experiment name: curious-echo
        - Directory name: curious-echo_a1b2c3d4

        Args:
            identifier: Experiment identifier (ID, short ID, or name)

        Returns:
            Full experiment ID if found, None otherwise
        """
        # First check if it's a directory name that exists
        if (self.base_dir / identifier).exists():
            # Extract experiment ID from directory name or manifest
            manifest_path = self.base_dir / identifier / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        return manifest.get("experiment_id")
                except (json.JSONDecodeError, OSError):
                    pass
            # Try to extract from directory name (format: name_shortid)
            if "_" in identifier:
                short_id = identifier.rsplit("_", 1)[1]
                if len(short_id) == 8 and all(
                    c in "0123456789abcdef" for c in short_id
                ):
                    return f"experiment_{short_id}"

        # Check if it's already a full experiment ID
        if identifier.startswith("experiment_"):
            # Look for directories ending with the short ID
            short_id = identifier.split("_")[1] if "_" in identifier else ""
            if short_id:
                for experiment_dir in self.base_dir.glob(f"*_{short_id}"):
                    if experiment_dir.is_dir():
                        return identifier

        # Check if it's a shortened ID (8 hex chars)
        if len(identifier) == 8 and all(c in "0123456789abcdef" for c in identifier):
            full_id = f"experiment_{identifier}"
            # Look for directories ending with this short ID
            for experiment_dir in self.base_dir.glob(f"*_{identifier}"):
                if experiment_dir.is_dir():
                    return full_id

        # Try to find by name
        found_by_name = self.find_experiment_by_name(identifier)
        if found_by_name:
            return found_by_name

        # Try partial ID match (e.g., user types just "a1b2")
        matches = []
        for experiment_dir in self.base_dir.iterdir():
            if not experiment_dir.is_dir() or experiment_dir.name in ["active", "logs"]:
                continue

            # Check if directory ends with partial ID
            if "_" in experiment_dir.name:
                short_id = experiment_dir.name.rsplit("_", 1)[1]
                if short_id.startswith(identifier):
                    full_id = f"experiment_{short_id}"
                    if full_id not in matches:
                        matches.append(full_id)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches, need more specific identifier
            logging.warning(f"Multiple experiments match '{identifier}': {matches}")

        return None

    def get_experiment_directory(self, experiment_id: str) -> Optional[str]:
        """Get the full directory name for an experiment ID.

        Args:
            experiment_id: The experiment ID (e.g., experiment_a1b2c3d4)

        Returns:
            Full directory name if found, None otherwise
        """
        # Extract short ID from experiment ID
        if experiment_id.startswith("experiment_") and "_" in experiment_id:
            short_id = experiment_id.split("_")[1]
            # Look for directories ending with this short ID
            for experiment_dir in self.base_dir.glob(f"*_{short_id}"):
                if experiment_dir.is_dir():
                    return experiment_dir.name

        # Fall back to checking manifest files
        for experiment_dir in self.base_dir.iterdir():
            if not experiment_dir.is_dir() or experiment_dir.name in ["active", "logs"]:
                continue
            manifest_path = experiment_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        if manifest.get("experiment_id") == experiment_id:
                            return experiment_dir.name
                except (json.JSONDecodeError, OSError):
                    pass

        return None
