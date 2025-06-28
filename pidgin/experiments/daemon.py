# pidgin/experiments/daemon.py
"""Unix daemon for running experiments in background."""

import os
import sys
import signal
import asyncio
import logging
from pathlib import Path
from typing import Optional


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
        self.log_file = pid_dir.parent.resolve() / "logs" / f"{experiment_id}.log"
        self.stop_requested = False
        
    def daemonize(self):
        """Daemonize using double-fork technique."""
        # First fork
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process, return and let it exit
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"Fork #1 failed: {e}\n")
            sys.exit(1)
            
        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)
        
        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Second parent, exit
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"Fork #2 failed: {e}\n")
            sys.exit(1)
            
        # Now we're in the daemon process
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Create log directory
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Open log file
        log_fd = open(self.log_file, 'a', buffering=1)  # Line buffered
        
        # Redirect stdout/stderr to log
        os.dup2(log_fd.fileno(), sys.stdout.fileno())
        os.dup2(log_fd.fileno(), sys.stderr.fileno())
        
        # Close stdin
        devnull = open('/dev/null', 'r')
        os.dup2(devnull.fileno(), sys.stdin.fileno())
        
        # Write PID file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
            
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)  # Ignore hangup
        
        # Log startup
        print(f"Daemon started for experiment {self.experiment_id} (PID: {os.getpid()})")
        
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
        # Import here to avoid circular imports
        from .storage import ExperimentStore
        
        # Update experiment status if still running
        try:
            # Get storage with proper path resolution
            project_base = os.environ.get('PIDGIN_PROJECT_BASE', '.')
            db_path = Path(project_base).resolve() / "pidgin_output" / "experiments" / "experiments.db"
            storage = ExperimentStore(db_path=db_path)
            
            # Check current status
            exp = storage.get_experiment(self.experiment_id)
            if exp and exp['status'] == 'running':
                # Mark as failed since we're cleaning up unexpectedly
                storage.update_experiment_status(self.experiment_id, 'failed')
                logging.info(f"Marked experiment {self.experiment_id} as failed on cleanup")
                
                # Also mark any running conversations as failed
                storage.mark_running_conversations_failed(self.experiment_id)
                
        except Exception as e:
            logging.error(f"Failed to update experiment status during cleanup: {e}")
        
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
