"""Launch and manage experiment daemon processes."""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from ..core.constants import SystemDefaults


class ProcessLauncher:
    """Handles launching and monitoring daemon processes."""

    def __init__(self, base_dir: Path):
        """Initialize process launcher.

        Args:
            base_dir: Base directory for experiments
        """
        self.base_dir = base_dir
        # Import get_cache_dir for active directory
        from ..io.directories import get_cache_dir

        self.active_dir = get_cache_dir() / "active_experiments"

    def build_daemon_command(
        self, experiment_id: str, dir_name: str, config, working_dir: str
    ) -> list:
        """Build the command to launch the daemon.

        Args:
            experiment_id: Experiment ID
            dir_name: Directory name for the experiment
            config: Experiment configuration
            working_dir: Working directory

        Returns:
            Command list for subprocess
        """
        # Check if setproctitle is available to make processes identifiable
        try:
            import setproctitle

            has_setproctitle = True
        except ImportError:
            has_setproctitle = False

        if has_setproctitle:
            # Create a wrapper script that sets process title before running
            proc_name = "pidgin-exp"
            config_json = json.dumps(config.dict())

            wrapper_script = f"""
import sys
try:
    import setproctitle
    setproctitle.setproctitle('{proc_name}')
except ImportError:
    pass
sys.argv = [
    'pidgin.experiments.daemon_launcher',
    '--experiment-id', '{experiment_id}',
    '--experiment-dir', '{dir_name}',
    '--config', {json.dumps(config_json)},
    '--working-dir', '{working_dir}'
]
import runpy
runpy.run_module('pidgin.experiments.daemon_launcher', run_name='__main__')
"""

            return [sys.executable, "-c", wrapper_script]
        else:
            # Fall back to regular command without process title
            return [
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

    def prepare_environment(self, working_dir: str) -> dict:
        """Prepare environment variables for subprocess.

        Args:
            working_dir: Working directory

        Returns:
            Environment dictionary
        """
        env = os.environ.copy()
        # Ensure PIDGIN_ORIGINAL_CWD is set for the subprocess
        if "PIDGIN_ORIGINAL_CWD" not in env:
            env["PIDGIN_ORIGINAL_CWD"] = working_dir

        # Log what we're passing to subprocess for debugging
        logging.debug(f"Passing {len(env)} environment variables to subprocess")
        logging.debug(f"ANTHROPIC_API_KEY in env: {'ANTHROPIC_API_KEY' in env}")
        logging.debug(f"OPENAI_API_KEY in env: {'OPENAI_API_KEY' in env}")

        return env

    def launch_detached_process(
        self, cmd: list, stdout_file, stderr_file, env: dict
    ) -> subprocess.Popen:
        """Launch a detached subprocess.

        Args:
            cmd: Command to run
            stdout_file: File handle for stdout
            stderr_file: File handle for stderr
            env: Environment variables

        Returns:
            Subprocess handle
        """
        # Use platform-specific flags for creating a detached process
        if sys.platform == "win32":
            # Windows: use CREATE_NEW_PROCESS_GROUP flag
            creationflags = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
            return subprocess.Popen(
                cmd,
                stdout=stdout_file,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL,
                env=env,
                creationflags=creationflags,
            )
        else:
            # Unix/Linux/macOS: use start_new_session to detach from terminal
            return subprocess.Popen(
                cmd,
                stdout=stdout_file,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL,
                env=env,
                start_new_session=True,  # Creates new session, detaches from terminal
            )

    def wait_for_daemon_start(
        self, experiment_id: str, process: subprocess.Popen
    ) -> bool:
        """Wait for daemon to start successfully.

        Args:
            experiment_id: Experiment ID
            process: Subprocess handle

        Returns:
            True if daemon started successfully
        """
        max_retries = SystemDefaults.MAX_RETRIES
        pid_file = self.active_dir / f"{experiment_id}.pid"

        # Wait for PID file to be created
        for i in range(max_retries * 2):  # Double retries for PID file creation
            time.sleep(0.5)

            # Check if subprocess exited early
            poll_result = process.poll()
            if poll_result is not None and poll_result != 0:
                # Process exited with error
                return False

            # Check if PID file exists first
            if pid_file.exists():
                # Now check if process is actually running
                if self._check_process_running(pid_file):
                    # Success!
                    return True
                else:
                    # PID file exists but process isn't running
                    return False

        return False

    def _check_process_running(self, pid_file: Path) -> bool:
        """Check if process referenced in PID file is running.

        Args:
            pid_file: Path to PID file

        Returns:
            True if process is running
        """
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, FileNotFoundError):
            return False

    def handle_startup_failure(
        self, experiment_id: str, process: subprocess.Popen, startup_log: Path
    ):
        """Handle daemon startup failure.

        Args:
            experiment_id: Experiment ID
            process: Subprocess handle
            startup_log: Path to startup log

        Raises:
            RuntimeError: With detailed error message
        """
        error_msg = "Failed to start experiment daemon"
        if startup_log.exists():
            try:
                with open(startup_log) as f:
                    error_content = f.read().strip()
                    if error_content:
                        error_msg += f"\nStartup error: {error_content}"
            except Exception:
                pass

        # Check if process failed immediately
        poll_result = process.poll()
        if poll_result is not None and poll_result != 0:
            # Process exited with error
            error_msg += f"\nExit code: {process.returncode}"
            error_msg += "\nCheck logs in experiment directory"
            error_msg += f"\nStartup log at: {startup_log}"
            raise RuntimeError(error_msg)

        error_msg += (
            f"\nPID file not created at: {self.active_dir / f'{experiment_id}.pid'}"
        )
        raise RuntimeError(error_msg)
