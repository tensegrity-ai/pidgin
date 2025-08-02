"""Tests for ConfigBuilder."""

from unittest.mock import MagicMock, patch

import pytest

from pidgin.cli.config_builder import ConfigBuilder
from pidgin.experiments import ExperimentConfig


class TestConfigBuilder:
    """Test ConfigBuilder functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = ConfigBuilder()

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.config_builder.display")
    def test_build_config_basic(
        self, mock_display, mock_get_config, mock_generate_name, mock_validate_model
    ):
        """Test basic config building."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Build config
        config, agent_a_name, agent_b_name = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
        )

        # Verify
        assert isinstance(config, ExperimentConfig)
        assert config.name == "test-experiment"
        assert config.agent_a_model == "claude-3-sonnet"
        assert config.agent_b_model == "gpt-4o"
        assert config.repetitions == 5
        assert config.max_turns == 10
        assert agent_a_name == "Claude 3 Sonnet"
        assert agent_b_name == "GPT-4o"

        # Check convergence profile was set
        mock_config.set.assert_called_once_with("convergence.profile", "balanced")

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.get_config")
    def test_build_config_with_name(self, mock_get_config, mock_validate_model):
        """Test config building with provided name."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Build config with name
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            name="my-experiment",
        )

        # Verify name was used
        assert config.name == "my-experiment"

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.config_builder.resolve_temperatures")
    def test_build_config_with_temperatures(
        self, mock_resolve_temps, mock_get_config, mock_generate_name, mock_validate_model
    ):
        """Test config building with temperature settings."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_resolve_temps.return_value = (0.7, 0.8)

        # Build config with temperatures
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            temperature=0.9,
            temp_a=0.7,
            temp_b=0.8,
        )

        # Verify
        mock_resolve_temps.assert_called_once_with(0.9, 0.7, 0.8)
        assert config.temperature_a == 0.7
        assert config.temperature_b == 0.8

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.config_builder.parse_dimensions")
    @patch("pidgin.cli.config_builder.build_initial_prompt")
    def test_build_config_with_dimensions(
        self,
        mock_build_prompt,
        mock_parse_dims,
        mock_get_config,
        mock_generate_name,
        mock_validate_model,
    ):
        """Test config building with dimensions."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_parse_dims.return_value = ["philosophy", "science"]
        mock_build_prompt.return_value = "Hello from philosophy and science"

        # Build config with dimensions
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            dimensions=["philosophy", "science"],
        )

        # Verify
        mock_parse_dims.assert_called_once_with(["philosophy", "science"])
        mock_build_prompt.assert_called_once_with("Hello", ["philosophy", "science"])
        assert config.dimensions == ["philosophy", "science"]
        assert config.custom_prompt == "Hello from philosophy and science"

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.config_builder.get_smart_convergence_defaults")
    @patch("pidgin.cli.config_builder.display")
    def test_build_config_with_smart_convergence(
        self,
        mock_display,
        mock_smart_defaults,
        mock_get_config,
        mock_generate_name,
        mock_validate_model,
    ):
        """Test config building with smart convergence defaults."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_smart_defaults.return_value = (0.85, "continue")

        # Build config without convergence settings
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
        )

        # Verify smart defaults were applied
        mock_smart_defaults.assert_called_once_with("claude-3-sonnet", "gpt-4o")
        assert config.convergence_threshold == 0.85
        assert config.convergence_action == "continue"
        mock_display.dim.assert_any_call(
            "Using default convergence threshold: 0.85 → continue"
        )

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    def test_build_config_with_explicit_convergence(
        self, mock_get_config, mock_generate_name, mock_validate_model
    ):
        """Test config building with explicit convergence settings."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Build config with explicit convergence
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            convergence_threshold=0.9,
            convergence_action="notify",
        )

        # Verify explicit values were used
        assert config.convergence_threshold == 0.9
        assert config.convergence_action == "notify"

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.config_builder.random.choice")
    def test_build_config_with_random_first_speaker(
        self, mock_random_choice, mock_get_config, mock_generate_name, mock_validate_model
    ):
        """Test config building with random first speaker."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_random_choice.return_value = "b"

        # Build config with random first speaker
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            first_speaker="random",
        )

        # Verify
        mock_random_choice.assert_called_once_with(["a", "b"])
        assert config.first_speaker == "agent_b"

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    def test_build_config_with_awareness_settings(
        self, mock_get_config, mock_generate_name, mock_validate_model
    ):
        """Test config building with awareness settings."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Build config with awareness
        config, _, _ = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            awareness=True,
            awareness_a=True,
            awareness_b=False,
            choose_names=True,
        )

        # Verify
        assert config.awareness is True
        assert config.awareness_a is True
        assert config.awareness_b is False
        assert config.choose_names is True

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.helpers.format_model_display")
    @patch("pidgin.cli.config_builder.display")
    def test_show_config_info(
        self,
        mock_display,
        mock_format_display,
        mock_get_config,
        mock_generate_name,
        mock_validate_model,
    ):
        """Test showing configuration info."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_format_display.side_effect = ["Claude", "GPT-4o"]

        # Build config
        config, agent_a_name, agent_b_name = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
            temp_a=0.7,
            convergence_threshold=0.85,
            convergence_action="stop",
        )

        # Show info
        self.builder.show_config_info(config, agent_a_name, agent_b_name, "Hello")

        # Verify display was called with correct info
        mock_display.info.assert_called_once()
        call_args = mock_display.info.call_args
        info_text = call_args[0][0]
        assert "Name: test-experiment" in info_text
        assert "Models: Claude ↔ GPT-4o" in info_text
        assert "Conversations: 5" in info_text
        assert "Turns per conversation: 10" in info_text
        assert "Temperature: A: 0.7" in info_text
        assert "Convergence: 0.85 → stop" in info_text

    @patch("pidgin.cli.config_builder.validate_model_id")
    @patch("pidgin.cli.config_builder.generate_experiment_name")
    @patch("pidgin.cli.config_builder.get_config")
    @patch("pidgin.cli.helpers.format_model_display")
    @patch("pidgin.cli.config_builder.display")
    def test_show_config_info_with_long_prompt(
        self,
        mock_display,
        mock_format_display,
        mock_get_config,
        mock_generate_name,
        mock_validate_model,
    ):
        """Test showing config info with long prompt."""
        # Setup mocks
        mock_validate_model.side_effect = [
            ("claude-3-sonnet", "Claude 3 Sonnet"),
            ("gpt-4o", "GPT-4o"),
        ]
        mock_generate_name.return_value = "test-experiment"
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_format_display.side_effect = ["Claude", "GPT-4o"]

        # Build config
        config, agent_a_name, agent_b_name = self.builder.build_config(
            agent_a="claude",
            agent_b="gpt",
            repetitions=5,
            max_turns=10,
        )

        # Show info with long prompt
        long_prompt = "This is a very long prompt that exceeds fifty characters and should be truncated"
        self.builder.show_config_info(config, agent_a_name, agent_b_name, long_prompt)

        # Verify truncation
        mock_display.info.assert_called_once()
        call_args = mock_display.info.call_args
        info_text = call_args[0][0]
        assert "Initial prompt: This is a very long prompt that exceeds fifty char..." in info_text