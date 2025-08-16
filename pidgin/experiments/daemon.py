# pidgin/experiments/daemon.py
"""Unix daemon for running experiments in background."""

import asyncio
import logging
import os
import signal
from pathlib import Path


class ExperimentDaemon:
    """Unix daemon for running experiments in background."""

    def __init__(self, experiment_id: str, pid_dir: Path):
        """Initialize daemon.

        Args:
            experiment_id: Unique experiment identifier
            pid_dir: Directory for PID files
        """
        self.experiment_id = experiment_id
        # Convert to absolute paths before daemonizing
        self.pid_file = pid_dir.resolve() / f"{experiment_id}.pid"
        # Note: log_file is not actually used - daemon_launcher sets up logging
        # We keep this for backward compatibility but it's unused
        self.log_file = None
        self.stop_requested = False

    def setup(self):
        """Set up the subprocess as a background process."""
        # Note: log directory is created by daemon_launcher.py, not here

        # Write PID file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        # Set process title for easier identification
        try:
            import setproctitle

            # Use simple name for daemon process
            setproctitle.setproctitle("pidgin-monitor")
        except ImportError:
            pass  # Optional dependency, graceful degradation

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)  # Ignore hangup

        # Log startup
        logging.info(
            f"Background process started for experiment {self.experiment_id} (PID: {os.getpid()})"
        )

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info(f"Received signal {signum}, requesting stop...")
        self.stop_requested = True

        # If we have an event loop running, stop it
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except RuntimeError:
            # No loop running
            pass

    def cleanup(self):
        """Clean up resources on exit."""
        # Remove PID file
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                logging.info(f"Removed PID file: {self.pid_file}")
            except Exception as e:
                logging.error(f"Failed to remove PID file: {e}")

    def is_stopping(self) -> bool:
        """Check if daemon should stop."""
        return self.stop_requested
