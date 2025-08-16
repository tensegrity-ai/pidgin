"""Manage experiment daemons and provide status."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ExperimentConfig
from .daemon_manager import DaemonManager
from .experiment_resolver import ExperimentResolver
from .experiment_status import ExperimentStatus


class ExperimentManager:
    """Manages experiment daemons and provides status.

    This is the main interface for experiment management, delegating
    specific responsibilities to specialized components:
    - ExperimentResolver: ID resolution and discovery
    - DaemonManager: Start/stop daemon processes
    - ExperimentStatus: Status checking and listing
    """

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
        # Import get_cache_dir for active directory
        from ..io.directories import get_cache_dir

        self.active_dir = get_cache_dir() / "active_experiments"
        # Store the database path but don't keep a connection open
        from ..io.paths import get_database_path

        self.db_path = get_database_path()

        # Initialize specialized components
        self.resolver = ExperimentResolver(base_dir)
        self.daemon_manager = DaemonManager(base_dir)
        self.status_handler = ExperimentStatus(base_dir)

        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)

    # Delegation methods for resolver
    def _find_experiment_by_name(self, name: str) -> Optional[str]:
        """Find experiment ID by name.

        Args:
            name: Experiment name to search for

        Returns:
            Experiment ID if found, None otherwise
        """
        return self.resolver.find_experiment_by_name(name)

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
        return self.resolver.resolve_experiment_id(identifier)

    def get_experiment_directory(self, experiment_id: str) -> Optional[str]:
        """Get the full directory name for an experiment ID.

        Args:
            experiment_id: The experiment ID (e.g., experiment_a1b2c3d4)

        Returns:
            Full directory name if found, None otherwise
        """
        return self.resolver.get_experiment_directory(experiment_id)

    # Delegation methods for daemon manager
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
        return self.daemon_manager.start_experiment(config, working_dir)

    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop running experiment gracefully.

        Args:
            experiment_id: Experiment to stop (ID, short ID, or name)

        Returns:
            True if stopped successfully
        """
        return self.daemon_manager.stop_experiment(experiment_id)

    def is_running(self, experiment_id: str) -> bool:
        """Check if experiment daemon is running.

        Args:
            experiment_id: Experiment to check

        Returns:
            True if daemon is running
        """
        return self.daemon_manager.is_running(experiment_id)

    def _get_pid(self, experiment_id: str) -> Optional[int]:
        """Get PID of running experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Process ID or None
        """
        return self.daemon_manager.get_pid(experiment_id)

    def cleanup_stale_pids(self):
        """Remove PID files for non-running processes."""
        self.daemon_manager.cleanup_stale_pids()

    # Delegation methods for status handler
    def list_experiments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all experiments with status.

        Args:
            limit: Maximum number of experiments to return

        Returns:
            List of experiment dictionaries
        """
        return self.status_handler.list_experiments(limit)

    def get_logs(self, experiment_id: str, lines: int = 50) -> List[str]:
        """Get recent log lines from experiment.

        Args:
            experiment_id: Experiment ID (ID, short ID, or name)
            lines: Number of lines to return

        Returns:
            List of log lines
        """
        return self.status_handler.get_logs(experiment_id, lines)

    def tail_logs(self, experiment_id: str, follow: bool = True):
        """Tail experiment logs (like tail -f).

        Args:
            experiment_id: Experiment ID (ID, short ID, or name)
            follow: Whether to follow the file
        """
        self.status_handler.tail_logs(experiment_id, follow)
