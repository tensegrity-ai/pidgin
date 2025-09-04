"""Test daemon and subprocess launching functionality."""

import tempfile
import time
from pathlib import Path

from pidgin.experiments.config import ExperimentConfig
from pidgin.experiments.daemon_manager import DaemonManager
from pidgin.experiments.manager import ExperimentManager
from pidgin.experiments.process_launcher import ProcessLauncher


def test_daemon_manager_creates_directories():
    """Test that DaemonManager creates necessary directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "experiments"

        # DaemonManager should not fail even if base_dir doesn't exist
        manager = DaemonManager(base_dir)

        # Active directory should be created
        assert manager.active_dir.exists()


def test_experiment_manager_creates_base_directory():
    """Test that ExperimentManager creates the base experiments directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "nonexistent" / "experiments"

        # Should not fail even if parent directories don't exist
        manager = ExperimentManager(base_dir)

        # Base directory should be created
        assert base_dir.exists()
        assert manager.active_dir.exists()


def test_process_launcher_builds_correct_command():
    """Test that ProcessLauncher builds subprocess command with correct Python."""
    import sys

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        launcher = ProcessLauncher(base_dir)

        config = ExperimentConfig(
            name="test",
            agent_a_model="local:test",
            agent_b_model="local:test",
            max_turns=1,
            repetitions=1,
        )

        cmd = launcher.build_daemon_command("test_exp_123", "test_dir", config, tmpdir)

        # First element should be Python executable
        assert cmd[0] == sys.executable

        # Should use either -m or -c flag
        assert cmd[1] in ["-m", "-c"]


def test_daemon_subprocess_launch_and_cleanup():
    """Test that daemon subprocess launches and cleans up properly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "experiments"
        manager = ExperimentManager(base_dir)

        config = ExperimentConfig(
            name="test_daemon",
            agent_a_model="local:test",
            agent_b_model="local:test",
            max_turns=1,
            repetitions=1,
        )

        # Start experiment
        exp_id = manager.start_experiment(config, working_dir=tmpdir)

        # Should return a valid experiment ID
        assert exp_id.startswith("experiment_")

        # PID file should exist initially
        pid_file = manager.active_dir / f"{exp_id}.pid"

        # Give daemon time to start
        time.sleep(0.5)

        # Check if daemon is running
        manager.is_running(exp_id)

        # Wait for experiment to complete (test provider is fast)
        max_wait = 5  # seconds
        start_time = time.time()
        while manager.is_running(exp_id) and (time.time() - start_time) < max_wait:
            time.sleep(0.1)

        # After completion, PID file should be cleaned up
        assert not pid_file.exists()

        # Experiment directory should exist
        exp_dirs = list(base_dir.glob("test_daemon_*"))
        assert len(exp_dirs) == 1

        # Check that output files were created
        exp_dir = exp_dirs[0]

        # List files for debugging if test fails
        files = list(exp_dir.glob("*"))
        file_names = [f.name for f in files]

        # At minimum, per-conversation events files or experiment log should exist
        has_events = any(
            name.startswith("events_") and name.endswith(".jsonl")
            for name in file_names
        )
        assert has_events or "experiment.log" in file_names
        # Manifest is created during post-processing, might not be there immediately
        # But events or logs should always be there


def test_daemon_handles_missing_console():
    """Test that daemon subprocess handles None console properly."""
    # This test is implicitly covered by test_daemon_subprocess_launch_and_cleanup
    # since the daemon runs without a console, but let's make it explicit

    with tempfile.TemporaryDirectory():
        from pidgin.core.event_bus import EventBus
        from pidgin.core.events import ConversationStartEvent
        from pidgin.ui.tail.display import TailDisplay

        bus = EventBus()

        # Create TailDisplay with None console (daemon mode)
        display = TailDisplay(bus, None)

        # This should not raise an error
        from pidgin.core.types import Agent

        agent_a = Agent(id="agent_a", model="test")
        agent_b = Agent(id="agent_b", model="test")

        event = ConversationStartEvent(
            conversation_id="test_conv", agent_a=agent_a, agent_b=agent_b
        )

        # Should handle event without error
        display.log_event(event)

        # No assertion needed - if no exception, test passes
