"""Manage experiment daemons and provide status."""

import json
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.constants import SystemDefaults
from ..core.exceptions import ExperimentAlreadyExistsError
from .config import ExperimentConfig


class ExperimentManager:
    """Manages experiment daemons and provides status."""

    def __init__(self, base_dir: Path = None):
        """Initialize manager.

        Args:
            base_dir: Base directory for experiments
        """
        if base_dir is None:
            # Use consistent path logic from paths module
            from ..io.paths import get_experiments_dir

            base_dir = get_experiments_dir()
        else:
            base_dir = base_dir.resolve()

        self.base_dir = base_dir
        self.active_dir = base_dir / "active"
        self.logs_dir = base_dir / "logs"
        # Store the database path but don't keep a connection open
        self.db_path = base_dir / "experiments.duckdb"

        # Ensure directories exist
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _find_experiment_by_name(self, name: str) -> Optional[str]:
        """Find experiment ID by name.

        Args:
            name: Experiment name to search for

        Returns:
            Experiment ID if found, None otherwise
        """
        for experiment_dir in self.base_dir.glob("experiment_*"):
            if not experiment_dir.is_dir():
                continue

            # Check manifest for name
            manifest_path = experiment_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        if manifest.get("name") == name:
                            return manifest.get("experiment_id", experiment_dir.name)
                except (json.JSONDecodeError, OSError):
                    # Manifest might be corrupted or inaccessible
                    pass

            # Also check if the name is in the directory name itself
            # Format: experiment_id_name_date
            if "_" in experiment_dir.name:
                parts = experiment_dir.name.split("_")
                if len(parts) >= 3:  # Has at least experiment_id_name
                    # Extract name part (between ID and date)
                    dir_name_parts = parts[2:-1] if len(parts) > 3 else [parts[2]]
                    dir_name = "_".join(dir_name_parts)
                    # Compare with sanitized input name
                    if dir_name == name.replace(" ", "-").replace("/", "-")[:30]:
                        return f"{parts[0]}_{parts[1]}"  # Return experiment_id

        return None

    def resolve_experiment_id(self, identifier: str) -> Optional[str]:
        """Resolve an experiment identifier to a full experiment ID.

        Supports:
        - Full experiment ID: experiment_a1b2c3d4
        - Shortened ID: a1b2c3d4
        - Experiment name: curious-echo
        - Directory name: experiment_a1b2c3d4_curious-echo_2025-01-10

        Args:
            identifier: Experiment identifier (ID, short ID, or name)

        Returns:
            Full experiment ID if found, None otherwise
        """
        # First check if it's a directory name that exists
        if (self.base_dir / identifier).exists():
            # Extract experiment ID from directory name
            if identifier.startswith("experiment_"):
                return identifier.split("_")[0] + "_" + identifier.split("_")[1]
            return identifier

        # Check if it's already a full experiment ID
        # Now we need to search for directories that start with this ID
        if identifier.startswith("experiment_"):
            for experiment_dir in self.base_dir.glob(f"{identifier}_*"):
                if experiment_dir.is_dir():
                    return identifier

        # Check if it's a shortened ID (add experiment_ prefix)
        if len(identifier) == 8 and all(c in "0123456789abcdef" for c in identifier):
            full_id = f"experiment_{identifier}"
            for experiment_dir in self.base_dir.glob(f"{full_id}_*"):
                if experiment_dir.is_dir():
                    return full_id

        # Try to find by name
        found_by_name = self._find_experiment_by_name(identifier)
        if found_by_name:
            return found_by_name

        # Try partial ID match (e.g., user types just "a1b2")
        matches = []
        for experiment_dir in self.base_dir.glob("experiment_*"):
            experiment_id = (
                experiment_dir.name.split("_")[0]
                + "_"
                + experiment_dir.name.split("_")[1]
                if "_" in experiment_dir.name
                else experiment_dir.name
            )
            if experiment_id.startswith(f"experiment_{identifier}"):
                if experiment_id not in matches:
                    matches.append(experiment_id)

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
        # Look for directories that start with this experiment ID
        for experiment_dir in self.base_dir.glob(f"{experiment_id}_*"):
            if experiment_dir.is_dir():
                return experiment_dir.name

        # If not found with underscore, try exact match
        if (self.base_dir / experiment_id).exists():
            return experiment_id

        return None

    def start_experiment(
        self, config: ExperimentConfig, working_dir: Optional[str] = None
    ) -> str:
        """Start experiment as daemon process.

        Args:
            config: Experiment configuration
            working_dir: Working directory to use for output (defaults to cwd)

        Returns:
            Experiment ID
        """
        # Generate a name if not provided
        if not config.name:
            from ..cli.name_generator import generate_experiment_name

            config.name = generate_experiment_name()
            logging.info(f"Generated experiment name: {config.name}")

        # Check for duplicate names
        existing = self._find_experiment_by_name(config.name)
        if existing:
            raise ExperimentAlreadyExistsError(config.name, existing)

        # Generate experiment ID
        experiment_id = f"experiment_{uuid.uuid4().hex[:8]}"

        # Create experiment directory with enhanced naming
        # Format: experiment_id_name_date
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_name = config.name.replace(" ", "-").replace("/", "-")[:30]  # Limit length
        dir_name = f"{experiment_id}_{safe_name}_{date_str}"

        experiment_dir = self.base_dir / dir_name
        experiment_dir.mkdir(parents=True, exist_ok=True)

        # Write initial metadata
        # Initial experiment state written to manifest.json by runner

        # Get working directory
        if working_dir is None:
            working_dir = os.getcwd()

        # Launch daemon process
        # Check if setproctitle is available to make processes identifiable
        try:
            import setproctitle  # noqa: F401
            has_setproctitle = True
        except ImportError:
            has_setproctitle = False

        if has_setproctitle:
            # Create a wrapper script that sets process title before running
            # Use meaningful name: pidgin-exp-{name}-{id}
            proc_name = f"pidgin-exp-{safe_name}-{experiment_id[:8]}"
            
            # Build the wrapper command with proper module execution
            wrapper_cmd = [
                sys.executable,
                "-c",
                f"import sys; import setproctitle; "
                f"setproctitle.setproctitle('{proc_name}'); "
                f"sys.argv = ['pidgin.experiments.daemon_launcher', "
                f"'--experiment-id', '{experiment_id}', "
                f"'--experiment-dir', '{dir_name}', "
                f"'--config', {json.dumps(config.dict())!r}, "
                f"'--working-dir', '{working_dir}']; "
                f"import runpy; "
                f"runpy.run_module('pidgin.experiments.daemon_launcher', "
                f"run_name='__main__')",
            ]
            cmd = wrapper_cmd
        else:
            # Fall back to regular command without process title
            cmd = [
                sys.executable,
                "-m",
                "pidgin.experiments.daemon_launcher",
                "--experiment-id",
                experiment_id,
                "--experiment-dir",
                dir_name,
                "--config",
                json.dumps(config.dict()),
                "--working-dir",
                working_dir,
            ]

        # Create a file to capture startup output
        startup_log = self.logs_dir / f"{experiment_id}_startup.log"

        # Start the daemon with output capture
        # Pass environment to subprocess so PIDGIN_ORIGINAL_CWD is available
        env = os.environ.copy()
        # Ensure PIDGIN_ORIGINAL_CWD is set for the subprocess
        if "PIDGIN_ORIGINAL_CWD" not in env:
            env["PIDGIN_ORIGINAL_CWD"] = working_dir

        with open(startup_log, "w") as stderr_file:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL,
                env=env,
            )

        # Wait for daemon to start with retries
        max_retries = SystemDefaults.MAX_RETRIES
        pid_file = self.active_dir / f"{experiment_id}.pid"

        # Wait for PID file to be created
        for i in range(max_retries * 2):  # Double retries for PID file creation
            time.sleep(0.5)

            # Check if subprocess exited early
            poll_result = process.poll()
            if poll_result is not None and poll_result != 0:
                break

            # Check if PID file exists first
            if pid_file.exists():
                # Now check if process is actually running
                if self.is_running(experiment_id):
                    # Success!
                    return experiment_id
                else:
                    # PID file exists but process isn't running
                    break

        # If we get here, daemon failed to start
        # Read any startup errors
        error_msg = "Failed to start experiment daemon"
        if startup_log.exists():
            try:
                with open(startup_log, "r") as f:
                    error_content = f.read().strip()
                    if error_content:
                        error_msg += f"\nStartup error: {error_content}"
            except Exception:
                pass

        # Check if process failed immediately
        if process.poll() is not None:
            error_msg += f"\nExit code: {process.returncode}"
            error_msg += f"\nCheck logs at: {self.logs_dir / f'{experiment_id}.log'}"
            error_msg += f"\nStartup log at: {startup_log}"
            raise RuntimeError(error_msg)

        error_msg += (
            f"\nPID file not created at: {self.active_dir / f'{experiment_id}.pid'}"
        )
        raise RuntimeError(error_msg)

    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop running experiment gracefully.

        Args:
            experiment_id: Experiment to stop (ID, short ID, or name)

        Returns:
            True if stopped successfully
        """
        # Resolve the identifier to a full experiment ID
        resolved_id = self.resolve_experiment_id(experiment_id)
        if not resolved_id:
            logging.error(f"Could not resolve experiment identifier: {experiment_id}")
            return False

        pid_file = self.active_dir / f"{resolved_id}.pid"

        if not pid_file.exists():
            return False

        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process exists
            try:
                os.kill(pid, 0)  # Check if process exists
            except ProcessLookupError:
                # Process doesn't exist, clean up PID file
                pid_file.unlink()
                return False

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            logging.info(f"Sent SIGTERM to PID {pid}")

            # Wait for process to exit (max 30 seconds)
            for i in range(30):
                try:
                    os.kill(pid, 0)  # Check if still running
                    time.sleep(1)
                except ProcessLookupError:
                    # Process has exited
                    return True

            # Force kill if still running
            logging.warning(f"Process {pid} didn't exit gracefully, sending SIGKILL")
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                # Already gone
                pass

            return True

        except Exception as e:
            logging.error(f"Error stopping experiment: {e}")
            return False

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
                    experiment_data["is_running"] = self.is_running(experiment_id)
                    if experiment_data["is_running"]:
                        experiment_data["pid"] = self._get_pid(experiment_id)

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

    def is_running(self, experiment_id: str) -> bool:
        """Check if experiment daemon is running.

        Args:
            experiment_id: Experiment to check

        Returns:
            True if daemon is running
        """
        pid_file = self.active_dir / f"{experiment_id}.pid"

        if not pid_file.exists():
            return False

        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, FileNotFoundError):
            # Clean up stale PID file
            if pid_file.exists():
                pid_file.unlink()
            return False

    def _get_pid(self, experiment_id: str) -> Optional[int]:
        """Get PID of running experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Process ID or None
        """
        pid_file = self.active_dir / f"{experiment_id}.pid"

        try:
            with open(pid_file) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            # PID file doesn't exist or contains invalid data
            return None

    def get_logs(self, experiment_id: str, lines: int = 50) -> List[str]:
        """Get recent log lines from experiment.

        Args:
            experiment_id: Experiment ID (ID, short ID, or name)
            lines: Number of lines to return

        Returns:
            List of log lines
        """
        # Resolve the identifier to a full experiment ID
        resolved_id = self.resolve_experiment_id(experiment_id)
        if not resolved_id:
            return [f"Could not resolve experiment identifier: {experiment_id}"]

        log_file = self.logs_dir / f"{resolved_id}.log"

        if not log_file.exists():
            return [f"No log file found at: {log_file}"]

        try:
            # Use tail-like behavior
            with open(log_file, "r") as f:
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
        resolved_id = self.resolve_experiment_id(experiment_id)
        if not resolved_id:
            logging.error(f"Could not resolve experiment identifier: {experiment_id}")
            return

        log_file = self.logs_dir / f"{resolved_id}.log"

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

    def cleanup_stale_pids(self):
        """Remove PID files for non-running processes."""
        if not self.active_dir.exists():
            return

        for pid_file in self.active_dir.glob("*.pid"):
            experiment_id = pid_file.stem
            if not self.is_running(experiment_id):
                logging.info(f"Removing stale PID file: {pid_file}")
                pid_file.unlink()
