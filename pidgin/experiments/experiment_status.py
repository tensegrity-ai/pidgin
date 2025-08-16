"""Handle experiment status checking and listing."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .daemon_manager import DaemonManager
from .experiment_resolver import ExperimentResolver


class ExperimentStatus:
    """Handles experiment status checking and listing."""

    def __init__(self, base_dir: Path):
        """Initialize status handler.

        Args:
            base_dir: Base directory for experiments
        """
        self.base_dir = base_dir
        self.resolver = ExperimentResolver(base_dir)
        self.daemon_manager = DaemonManager(base_dir)

    def list_experiments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all experiments with status.

        Args:
            limit: Maximum number of experiments to return

        Returns:
            List of experiment dictionaries
        """
        experiments = []

        # Read from experiment directories
        for experiment_dir in self.base_dir.iterdir():
            if not experiment_dir.is_dir() or experiment_dir.name in ["active", "logs"]:
                continue

            # Skip if it doesn't match our pattern (experiment_*)
            if not experiment_dir.name.startswith("experiment_"):
                continue

            manifest_path = experiment_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        experiment_data = json.load(f)

                    # Add runtime status
                    experiment_id = experiment_data["experiment_id"]
                    experiment_data["is_running"] = self.daemon_manager.is_running(
                        experiment_id
                    )
                    if experiment_data["is_running"]:
                        experiment_data["pid"] = self.daemon_manager.get_pid(
                            experiment_id
                        )

                    # Add directory name for display
                    experiment_data["directory"] = experiment_dir.name

                    experiments.append(experiment_data)
                except Exception as e:
                    logging.warning(
                        f"Failed to read experiment {experiment_dir.name}: {e}"
                    )

        # Sort by creation time (newest first)
        experiments.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Apply limit
        return experiments[:limit]

    def get_logs(self, experiment_id: str, lines: int = 50) -> List[str]:
        """Get recent log lines from experiment.

        Args:
            experiment_id: Experiment ID (ID, short ID, or name)
            lines: Number of lines to return

        Returns:
            List of log lines
        """
        # Resolve the identifier to a full experiment ID
        resolved_id = self.resolver.resolve_experiment_id(experiment_id)
        if not resolved_id:
            return [f"Could not resolve experiment identifier: {experiment_id}"]

        # Get log file from experiment directory
        dir_name = self.resolver.get_experiment_directory(resolved_id)
        if not dir_name:
            return [f"Could not find experiment directory for: {experiment_id}"]

        log_file = self.base_dir / dir_name / "experiment.log"

        if not log_file.exists():
            return [f"No log file found at: {log_file}"]

        try:
            # Use tail-like behavior
            with open(log_file) as f:
                # Read all lines for small files
                all_lines = f.readlines()
                if len(all_lines) <= lines:
                    return all_lines
                else:
                    return all_lines[-lines:]
        except Exception as e:
            return [f"Error reading log file: {e}"]

    def tail_logs(self, experiment_id: str, follow: bool = True):
        """Tail experiment logs (like tail -f).

        Args:
            experiment_id: Experiment ID (ID, short ID, or name)
            follow: Whether to follow the file
        """
        # Resolve the identifier to a full experiment ID
        resolved_id = self.resolver.resolve_experiment_id(experiment_id)
        if not resolved_id:
            logging.error(f"Could not resolve experiment identifier: {experiment_id}")
            return

        # Get log file from experiment directory
        dir_name = self.resolver.get_experiment_directory(resolved_id)
        if not dir_name:
            logging.error(f"Could not find experiment directory for: {experiment_id}")
            return

        log_file = self.base_dir / dir_name / "experiment.log"

        if not log_file.exists():
            logging.warning(f"No log file found at: {log_file}")
            return

        # Use subprocess to tail
        cmd = ["tail"]
        if follow:
            cmd.append("-f")
        cmd.append(str(log_file))

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            # Normal exit
            pass
