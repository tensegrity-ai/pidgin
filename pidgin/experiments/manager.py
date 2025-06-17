"""Manage experiment daemons and provide status."""

import os
import sys
import json
import signal
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .storage import ExperimentStore
from .config import ExperimentConfig


class ExperimentManager:
    """Manages experiment daemons and provides status."""
    
    def __init__(self, base_dir: Path = None):
        """Initialize manager.
        
        Args:
            base_dir: Base directory for experiments
        """
        if base_dir is None:
            # Check if we're in a daemon context
            project_base = os.environ.get('PIDGIN_PROJECT_BASE')
            if project_base:
                base_dir = Path(project_base) / "pidgin_output" / "experiments"
            else:
                base_dir = Path("./pidgin_output/experiments").resolve()
        else:
            base_dir = base_dir.resolve()
            
        self.base_dir = base_dir
        self.active_dir = base_dir / "active"
        self.logs_dir = base_dir / "logs"
        # Use the same database path as the base_dir
        db_path = base_dir / "experiments.db"
        self.storage = ExperimentStore(db_path=db_path)
        
        # Ensure directories exist
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def start_experiment(self, config: ExperimentConfig, working_dir: Optional[str] = None) -> str:
        """Start experiment as daemon process.
        
        Args:
            config: Experiment configuration
            working_dir: Working directory to use for output (defaults to cwd)
            
        Returns:
            Experiment ID
        """
        # Create experiment record
        exp_id = self.storage.create_experiment(config.name, config.dict())
        
        # Get working directory
        if working_dir is None:
            working_dir = os.getcwd()
        
        # Debug log
        logging.info(f"Starting experiment {exp_id} with working_dir: {working_dir}")
        
        # Launch daemon process
        cmd = [
            sys.executable, "-m", "pidgin.experiments.daemon_launcher",
            "--experiment-id", exp_id,
            "--config", json.dumps(config.dict()),
            "--working-dir", working_dir
        ]
        
        
        # Start the daemon
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        
        # Wait briefly for daemon to start
        time.sleep(1.0)
        
        # Verify it started
        if not self.is_running(exp_id):
            # Check if process failed immediately
            if process.poll() is not None:
                raise RuntimeError(
                    f"Failed to start experiment daemon (exit code: {process.returncode}). "
                    f"Check logs at: {self.logs_dir / f'{exp_id}.log'}"
                )
            raise RuntimeError("Failed to start experiment daemon")
            
        return exp_id
        
    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop running experiment gracefully.
        
        Args:
            experiment_id: Experiment to stop
            
        Returns:
            True if stopped successfully
        """
        pid_file = self.active_dir / f"{experiment_id}.pid"
        
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
        experiments = self.storage.list_experiments(limit=limit)
        
        # Add running status
        for exp in experiments:
            exp['is_running'] = self.is_running(exp['experiment_id'])
            if exp['is_running']:
                exp['pid'] = self._get_pid(exp['experiment_id'])
                
        return experiments
        
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
        except:
            return None
            
    def get_logs(self, experiment_id: str, lines: int = 50) -> List[str]:
        """Get recent log lines from experiment.
        
        Args:
            experiment_id: Experiment ID
            lines: Number of lines to return
            
        Returns:
            List of log lines
        """
        log_file = self.logs_dir / f"{experiment_id}.log"
        
        if not log_file.exists():
            return [f"No log file found at: {log_file}"]
            
        try:
            # Use tail-like behavior
            with open(log_file, 'r') as f:
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
            experiment_id: Experiment ID
            follow: Whether to follow the file
        """
        log_file = self.logs_dir / f"{experiment_id}.log"
        
        if not log_file.exists():
            print(f"No log file found at: {log_file}")
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
            exp_id = pid_file.stem
            if not self.is_running(exp_id):
                logging.info(f"Removing stale PID file: {pid_file}")
                pid_file.unlink()