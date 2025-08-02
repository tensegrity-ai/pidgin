"""Tests for DaemonLauncher."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from pidgin.cli.daemon_launcher import DaemonLauncher
from pidgin.experiments import ExperimentConfig


class TestDaemonLauncher:
    """Test DaemonLauncher functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = MagicMock()
        self.launcher = DaemonLauncher(console=self.console)
        # Mock the display attribute
        self.launcher.display = MagicMock()
        
        # Create a basic config for testing
        self.config = ExperimentConfig(
            name="test-experiment",
            agent_a_model="claude-3-sonnet",
            agent_b_model="gpt-4o",
            repetitions=5,
            max_turns=10,
        )

    @patch("pidgin.cli.daemon_launcher.get_model_config")
    @patch("pidgin.cli.daemon_launcher.APIKeyManager")
    @patch("pidgin.io.jsonl_reader.JSONLExperimentReader")
    def test_validate_before_start_success(
        self, mock_reader_class, mock_api_manager, mock_get_model_config
    ):
        """Test successful validation before starting."""
        # Setup mocks
        mock_reader = MagicMock()
        mock_reader.list_experiments.return_value = []  # No existing experiments
        mock_reader_class.return_value = mock_reader
        
        mock_get_model_config.side_effect = [
            MagicMock(provider="anthropic"),
            MagicMock(provider="openai"),
        ]
        
        # Should not raise any exceptions
        self.launcher.validate_before_start(self.config)
        
        # Verify API key validation was called
        mock_api_manager.validate_required_providers.assert_called_once()
        # Check that the call was made with a list containing both providers (order doesn't matter)
        call_args = mock_api_manager.validate_required_providers.call_args[0][0]
        assert set(call_args) == {"anthropic", "openai"}

    @patch("pidgin.io.jsonl_reader.JSONLExperimentReader")
    def test_validate_before_start_existing_experiment(self, mock_reader_class):
        """Test validation fails when experiment already exists."""
        # Setup mocks
        mock_reader = MagicMock()
        mock_reader.list_experiments.return_value = [
            {"name": "test-experiment", "id": "existing-id"}
        ]
        mock_reader_class.return_value = mock_reader
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Experiment 'test-experiment' already exists"):
            self.launcher.validate_before_start(self.config)
        
        # Verify error was displayed
        self.launcher.display.error.assert_called_once()

    @patch("pidgin.cli.daemon_launcher.get_model_config")
    @patch("pidgin.cli.daemon_launcher.APIKeyManager")
    @patch("pidgin.io.jsonl_reader.JSONLExperimentReader")
    def test_validate_before_start_missing_api_keys(
        self, mock_reader_class, mock_api_manager, mock_get_model_config
    ):
        """Test validation fails when API keys are missing."""
        # Setup mocks
        mock_reader = MagicMock()
        mock_reader.list_experiments.return_value = []
        mock_reader_class.return_value = mock_reader
        
        mock_get_model_config.side_effect = [
            MagicMock(provider="anthropic"),
            MagicMock(provider="openai"),
        ]
        
        # Simulate API key validation failure
        mock_api_manager.validate_required_providers.side_effect = Exception(
            "Missing API key for provider: anthropic"
        )
        
        # Should raise exception
        with pytest.raises(Exception, match="Missing API key"):
            self.launcher.validate_before_start(self.config)
        
        # Verify error was displayed
        self.launcher.display.error.assert_called_with(
            "Missing API key for provider: anthropic",
            title="Missing API Keys",
            use_panel=True,
        )

    @patch("pidgin.io.jsonl_reader.JSONLExperimentReader")
    def test_validate_before_start_invalid_config(self, mock_reader_class):
        """Test validation fails when config is invalid."""
        # Setup mocks
        mock_reader = MagicMock()
        mock_reader.list_experiments.return_value = []
        mock_reader_class.return_value = mock_reader
        
        # Create invalid config
        invalid_config = ExperimentConfig(
            name="",  # Invalid empty name
            agent_a_model="claude-3-sonnet",
            agent_b_model="gpt-4o",
            repetitions=0,  # Invalid repetitions
            max_turns=10,
        )
        
        # Mock validate to return errors
        invalid_config.validate = MagicMock(
            return_value=["Name cannot be empty", "Repetitions must be positive"]
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Configuration validation failed"):
            self.launcher.validate_before_start(invalid_config)
        
        # Verify error display
        self.launcher.display.error.assert_called_once()
        call_args = self.launcher.display.error.call_args
        assert "Name cannot be empty" in call_args[0][0]
        assert "Repetitions must be positive" in call_args[0][0]

    @patch("pidgin.cli.daemon_launcher.ExperimentManager")
    @patch("pidgin.cli.daemon_launcher.get_model_config")
    @patch("pidgin.cli.daemon_launcher.APIKeyManager")
    @patch("pidgin.io.jsonl_reader.JSONLExperimentReader")
    def test_start_daemon_success(
        self, mock_reader_class, mock_api_manager, mock_get_model_config, mock_manager_class
    ):
        """Test successful daemon start."""
        # Setup mocks for validation
        mock_reader = MagicMock()
        mock_reader.list_experiments.return_value = []
        mock_reader_class.return_value = mock_reader
        
        mock_get_model_config.side_effect = [
            MagicMock(provider="anthropic"),
            MagicMock(provider="openai"),
        ]
        
        # Setup experiment manager mock
        mock_manager = MagicMock()
        mock_manager.start_experiment.return_value = "exp-12345678"
        mock_manager_class.return_value = mock_manager
        
        # Start daemon
        exp_id = self.launcher.start_daemon(self.config)
        
        # Verify
        assert exp_id == "exp-12345678"
        mock_manager.start_experiment.assert_called_once()
        self.console.print.assert_called_with("\n[#a3be8c]✓ Started: exp-12345678[/#a3be8c]")

    @patch("pidgin.cli.daemon_launcher.ExperimentManager")
    @patch("pidgin.cli.daemon_launcher.get_model_config")
    @patch("pidgin.cli.daemon_launcher.APIKeyManager")
    @patch("pidgin.io.jsonl_reader.JSONLExperimentReader")
    def test_start_daemon_failure(
        self, mock_reader_class, mock_api_manager, mock_get_model_config, mock_manager_class
    ):
        """Test daemon start failure."""
        # Setup mocks for validation
        mock_reader = MagicMock()
        mock_reader.list_experiments.return_value = []
        mock_reader_class.return_value = mock_reader
        
        mock_get_model_config.side_effect = [
            MagicMock(provider="anthropic"),
            MagicMock(provider="openai"),
        ]
        
        # Setup experiment manager to fail
        mock_manager = MagicMock()
        mock_manager.start_experiment.side_effect = Exception("Failed to create daemon")
        mock_manager_class.return_value = mock_manager
        
        # Should raise exception
        with pytest.raises(Exception, match="Failed to create daemon"):
            self.launcher.start_daemon(self.config)
        
        # Verify error display
        self.launcher.display.error.assert_called_with(
            "Failed to start experiment: Failed to create daemon",
            use_panel=True,
        )

    def test_show_quiet_mode_info(self):
        """Test showing quiet mode information."""
        self.launcher.show_quiet_mode_info("exp-12345678", "test-experiment")
        
        # Verify console output
        self.console.print.assert_called_with(
            "\n[#4c566a]Running in background. Check progress:[/#4c566a]"
        )
        
        # Verify commands were shown
        self.launcher.display.info.assert_called_once()
        call_args = self.launcher.display.info.call_args
        info_text = call_args[0][0]
        assert "pidgin monitor" in info_text
        assert "pidgin stop test-experiment" in info_text
        assert "pidgin stop exp-1234" in info_text
        assert "tail -f" in info_text

    def test_show_interactive_mode_info(self):
        """Test showing interactive mode information."""
        self.launcher.show_interactive_mode_info()
        
        # Verify console output
        self.console.print.assert_any_call(
            "[#4c566a]Ctrl+C to exit display • experiment continues[/#4c566a]"
        )
        self.console.print.assert_any_call()

    @pytest.mark.asyncio
    @patch("pidgin.experiments.display_runner.run_display")
    @patch("pidgin.cli.daemon_launcher.ExperimentManager")
    async def test_run_display_and_handle_completion_success(
        self, mock_manager_class, mock_run_display
    ):
        """Test running display and handling completion."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_experiment_directory.return_value = "exp-12345678"
        mock_manager_class.return_value = mock_manager
        
        # Mock manifest file
        manifest_data = {
            "completed_conversations": 5,
            "failed_conversations": 0,
            "total_conversations": 5,
            "status": "completed",
            "started_at": "2024-01-01T10:00:00Z",
            "completed_at": "2024-01-01T10:30:00Z",
        }
        
        with patch("pidgin.cli.daemon_launcher.open", mock_open(read_data=json.dumps(manifest_data))):
            with patch("pidgin.cli.daemon_launcher.Path.exists", return_value=True):
                with patch("pidgin.cli.daemon_launcher.send_notification") as mock_notify:
                    await self.launcher.run_display_and_handle_completion(
                        "exp-12345678", "test-experiment", "chat", True, 5
                    )
        
        # Verify display was run
        mock_run_display.assert_called_once_with("exp-12345678", "chat")
        
        # Verify completion info was shown
        self.launcher.display.experiment_complete.assert_called_once()
        call_kwargs = self.launcher.display.experiment_complete.call_args.kwargs
        assert call_kwargs["name"] == "test-experiment"
        assert call_kwargs["completed"] == 5
        assert call_kwargs["failed"] == 0
        assert call_kwargs["total"] == 5
        assert call_kwargs["status"] == "completed"
        
        # Verify notification was sent
        mock_notify.assert_called_once_with(
            title="Pidgin Experiment Complete",
            message="Experiment 'test-experiment' has finished (5/5 conversations)",
        )

    @pytest.mark.asyncio
    @patch("pidgin.experiments.display_runner.run_display")
    @patch("pidgin.cli.daemon_launcher.ExperimentManager")
    async def test_run_display_keyboard_interrupt(
        self, mock_manager_class, mock_run_display
    ):
        """Test handling keyboard interrupt during display."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_experiment_directory.return_value = "exp-12345678"
        mock_manager_class.return_value = mock_manager
        
        # Simulate KeyboardInterrupt
        mock_run_display.side_effect = KeyboardInterrupt()
        
        await self.launcher.run_display_and_handle_completion(
            "exp-12345678", "test-experiment", "chat", False, 5
        )
        
        # Verify interrupt was handled gracefully
        self.console.print.assert_any_call()
        self.launcher.display.info.assert_called_with(
            "Display exited. Experiment continues running in background.",
            use_panel=False,
        )
        self.console.print.assert_any_call("\n[#4c566a]Check progress with:[/#4c566a]")
        self.console.print.assert_any_call("  pidgin monitor")
        self.console.print.assert_any_call("  pidgin stop test-experiment")

    @patch("pidgin.cli.daemon_launcher.get_model_config")
    def test_get_required_providers(self, mock_get_model_config):
        """Test getting required providers from config."""
        # Setup mocks
        mock_get_model_config.side_effect = [
            MagicMock(provider="anthropic"),
            MagicMock(provider="openai"),
        ]
        
        providers = self.launcher._get_required_providers(self.config)
        
        assert providers == {"anthropic", "openai"}

    def test_show_completion_info_no_manifest(self):
        """Test showing completion info when manifest doesn't exist."""
        with patch("pidgin.cli.daemon_launcher.Path.exists", return_value=False):
            self.launcher._show_completion_info(
                "exp-12345678", "exp-12345678", "test-experiment", False, 5
            )
        
        # Should show generic message
        self.launcher.display.info.assert_called_with(
            "Display exited. Experiment continues running in background.",
            use_panel=False,
        )