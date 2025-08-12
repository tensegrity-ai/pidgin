"""Manage experiment daemon processes."""

import logging
import os
import signal
import time
import uuid
from pathlib import Path
from typing import Optional

from ..core.exceptions import ExperimentAlreadyExistsError
from .config import ExperimentConfig
from .experiment_resolver import ExperimentResolver
from .process_launcher import ProcessLauncher


class DaemonManager:
    """Manages experiment daemon processes."""

    def __init__(self, base_dir: Path):
        """Initialize daemon manager.

        Args:
            base_dir: Base directory for experiments
        """
        self.base_dir = base_dir
        # Import get_cache_dir for active directory
        from ..io.directories import get_cache_dir

        self.active_dir = get_cache_dir() / "active_experiments"
        self.resolver = ExperimentResolver(base_dir)
        self.launcher = ProcessLauncher(self.base_dir)

        # Ensure directories exist
        self.active_dir.mkdir(parents=True, exist_ok=True)

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
        existing = self.resolver.find_experiment_by_name(config.name)
        if existing:
            raise ExperimentAlreadyExistsError(config.name, existing)

        # Generate experiment ID
        experiment_id = f"experiment_{uuid.uuid4().hex[:8]}"

        # Create experiment directory with simplified naming
        # Format: name_shortid (e.g., "curious-echo_a1b2c3d4")
        safe_name = config.name.replace(" ", "-").replace("/", "-")[:30]  # Limit length
        short_id = experiment_id.split("_")[1]  # Just the hex part
        dir_name = f"{safe_name}_{short_id}"

        experiment_dir = self.base_dir / dir_name
        experiment_dir.mkdir(parents=True, exist_ok=True)

        # Get working directory
        if working_dir is None:
            working_dir = os.getcwd()

        # Launch daemon process
        cmd = self.launcher.build_daemon_command(
            experiment_id, dir_name, config, working_dir
        )

        # Create log files in experiment directory
        exp_dir = self.base_dir / dir_name
        startup_log = exp_dir / "startup.log"
        experiment_log = exp_dir / "experiment.log"

        # Start the subprocess as a detached process
        env = self.launcher.prepare_environment(working_dir)

        with (
            open(startup_log, "w") as stderr_file,
            open(experiment_log, "w") as stdout_file,
        ):
            process = self.launcher.launch_detached_process(
                cmd, stdout_file, stderr_file, env
            )

        # Wait for daemon to start
        if self.launcher.wait_for_daemon_start(experiment_id, process):
            return experiment_id

        # If we get here, daemon failed to start
        self.launcher.handle_startup_failure(experiment_id, process, startup_log)
        return experiment_id  # Return the ID even if startup failed

    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop running experiment gracefully.

        Args:
            experiment_id: Experiment to stop (ID, short ID, or name)

        Returns:
            True if stopped successfully
        """
        # Resolve the identifier to a full experiment ID
        resolved_id = self.resolver.resolve_experiment_id(experiment_id)
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

    def get_pid(self, experiment_id: str) -> Optional[int]:
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

    def cleanup_stale_pids(self):
        """Remove PID files for non-running processes."""
        if not self.active_dir.exists():
            return

        for pid_file in self.active_dir.glob("*.pid"):
            experiment_id = pid_file.stem
            if not self.is_running(experiment_id):
                logging.info(f"Removing stale PID file: {pid_file}")
                pid_file.unlink()
