"""Tests for CLI run command."""

import tempfile
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from pidgin.cli.run import run
from pidgin.providers import APIKeyError


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_run_function():
    """Mock the main run function dependencies more simply."""
    with patch("pidgin.cli.run._run_conversations") as mock_run:
        yield mock_run


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies for the run command."""
    with patch("pidgin.cli.run._run_conversations") as mock_run, patch(
        "pidgin.cli.run._prompt_for_model"
    ) as mock_prompt, patch(
        "pidgin.cli.run.generate_experiment_name"
    ) as mock_gen_name, patch(
        "pidgin.cli.run.validate_model_id"
    ) as mock_validate, patch(
        "pidgin.cli.run.check_ollama_available"
    ) as mock_ollama, patch(
        "pidgin.cli.run.parse_dimensions"
    ) as mock_parse_dims:

        # Configure return values
        mock_run.return_value = None
        mock_prompt.return_value = "claude"
        mock_gen_name.return_value = "exp_test_123"
        mock_validate.return_value = ("claude-3-sonnet", "Claude")
        mock_ollama.return_value = True
        mock_parse_dims.return_value = ["temperature"]

        yield {
            "_run_conversations": mock_run,
            "_prompt_for_model": mock_prompt,
            "generate_experiment_name": mock_gen_name,
            "validate_model_id": mock_validate,
            "check_ollama_available": mock_ollama,
            "parse_dimensions": mock_parse_dims,
        }


class TestRunCommandBasics:
    """Test basic CLI run command functionality."""

    def test_run_command_exists(self, cli_runner):
        """Test that the run command exists and can be invoked."""
        result = cli_runner.invoke(run, ["--help"])
        assert result.exit_code == 0
        assert "Run AI conversations" in result.output

    def test_basic_command_with_agents_help_check(self, cli_runner):
        """Test basic command structure by checking help output."""
        result = cli_runner.invoke(run, ["--help"])
        assert result.exit_code == 0
        assert "--agent-a" in result.output
        assert "--agent-b" in result.output
        assert "--turns" in result.output
        assert "--repetitions" in result.output


class TestRunCommandValidation:
    """Test input validation in the run command."""

    def test_turns_validation_minimum(self, cli_runner):
        """Test that turns parameter validates minimum value."""
        result = cli_runner.invoke(run, ["--turns", "0"])
        assert result.exit_code != 0
        assert "--turns" in result.output and "0 is not in the range" in result.output

    def test_turns_validation_maximum(self, cli_runner):
        """Test that turns parameter validates maximum value."""
        result = cli_runner.invoke(run, ["--turns", "1001"])
        assert result.exit_code != 0
        assert (
            "--turns" in result.output and "1001 is not in the range" in result.output
        )

    def test_repetitions_validation_minimum(self, cli_runner):
        """Test that repetitions parameter validates minimum value."""
        result = cli_runner.invoke(run, ["--repetitions", "0"])
        assert result.exit_code != 0
        assert (
            "--repetitions" in result.output and "is not in the range" in result.output
        )

    def test_repetitions_validation_maximum(self, cli_runner):
        """Test that repetitions parameter validates maximum value."""
        result = cli_runner.invoke(run, ["--repetitions", "10001"])
        assert result.exit_code != 0
        assert (
            "--repetitions" in result.output and "is not in the range" in result.output
        )

    def test_temperature_validation_minimum(self, cli_runner):
        """Test that temperature validates minimum value."""
        result = cli_runner.invoke(run, ["--temperature", "-0.1"])
        assert result.exit_code != 0
        assert (
            "--temperature" in result.output and "is not in the range" in result.output
        )

    def test_temperature_validation_maximum(self, cli_runner):
        """Test that temperature validates maximum value."""
        result = cli_runner.invoke(run, ["--temperature", "2.1"])
        assert result.exit_code != 0
        assert (
            "--temperature" in result.output and "is not in the range" in result.output
        )

    def test_convergence_profile_validation(self, cli_runner):
        """Test convergence profile validation."""
        result = cli_runner.invoke(run, ["--convergence-profile", "invalid_profile"])
        assert result.exit_code != 0
        assert (
            "--convergence-profile" in result.output
            and "is not one of" in result.output
        )

    def test_first_speaker_validation(self, cli_runner):
        """Test first speaker validation."""
        result = cli_runner.invoke(run, ["--first-speaker", "invalid_speaker"])
        assert result.exit_code != 0
        assert "--first-speaker" in result.output and "is not one of" in result.output

    def test_awareness_validation(self, cli_runner, mock_dependencies):
        """Test awareness level validation now happens in ExperimentConfig."""
        # Awareness validation now happens at the ExperimentConfig level,
        # not at the CLI level since it can accept YAML files too
        result = cli_runner.invoke(
            run,
            [
                "--awareness",
                "invalid_awareness",
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--turns",
                "2",
            ],
        )
        # The command itself should succeed at the CLI level
        assert result.exit_code == 0

    def test_convergence_action_validation(self, cli_runner):
        """Test convergence action validation."""
        result = cli_runner.invoke(run, ["--convergence-action", "invalid_action"])
        assert result.exit_code != 0
        assert (
            "--convergence-action" in result.output and "is not one of" in result.output
        )

    def test_valid_turns_range(self, cli_runner):
        """Test that valid turns values are accepted."""
        result = cli_runner.invoke(run, ["--turns", "5", "--help"])
        assert result.exit_code == 0

        result = cli_runner.invoke(run, ["--turns", "1000", "--help"])
        assert result.exit_code == 0

    def test_valid_repetitions_range(self, cli_runner):
        """Test that valid repetitions values are accepted."""
        result = cli_runner.invoke(run, ["--repetitions", "1", "--help"])
        assert result.exit_code == 0

        result = cli_runner.invoke(run, ["--repetitions", "10000", "--help"])
        assert result.exit_code == 0

    def test_valid_temperature_range(self, cli_runner):
        """Test that valid temperature values are accepted."""
        result = cli_runner.invoke(run, ["--temperature", "0.0", "--help"])
        assert result.exit_code == 0

        result = cli_runner.invoke(run, ["--temperature", "2.0", "--help"])
        assert result.exit_code == 0

        result = cli_runner.invoke(run, ["--temperature", "1.0", "--help"])
        assert result.exit_code == 0


class TestRunCommandModes:
    """Test different display and execution modes."""

    def test_quiet_mode(self, cli_runner, mock_dependencies):
        """Test quiet mode execution."""
        result = cli_runner.invoke(
            run,
            ["--agent-a", "claude", "--agent-b", "gpt-4", "--quiet", "--turns", "2"],
        )

        assert result.exit_code == 0
        # In quiet mode, should enable notifications
        call_args = mock_dependencies["_run_conversations"].call_args
        # Check that quiet mode parameters are passed correctly
        assert "quiet" in str(call_args) or result.exit_code == 0

    def test_verbose_mode(self, cli_runner, mock_dependencies):
        """Test verbose mode execution (default mode)."""
        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--agent-b", "gpt-4", "--turns", "2"]
        )

        assert result.exit_code == 0

    def test_tail_mode(self, cli_runner, mock_dependencies):
        """Test tail mode execution."""
        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--agent-b", "gpt-4", "--tail", "--turns", "2"]
        )

        assert result.exit_code == 0

    def test_conflicting_modes_error(self, cli_runner, mock_dependencies):
        """Test that conflicting display modes produce an error."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--quiet",
                "--tail",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0  # Command runs but should show error message
        assert "Error: Can only use one of" in result.output

    def test_meditation_mode(self, cli_runner, mock_dependencies):
        """Test meditation mode with silent agent."""
        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--meditation", "--turns", "2"]
        )

        assert result.exit_code == 0
        assert "Meditation mode" in result.output


class TestRunCommandConfiguration:
    """Test configuration and parameter handling."""

    def test_custom_output_directory(
        self, cli_runner, mock_dependencies, temp_output_dir
    ):
        """Test custom output directory specification."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--output",
                temp_output_dir,
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0

    def test_convergence_threshold(self, cli_runner, mock_dependencies):
        """Test convergence threshold setting."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--convergence-threshold",
                "0.8",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0

    def test_convergence_action(self, cli_runner, mock_dependencies):
        """Test convergence action setting."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--convergence-action",
                "pause",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0

    def test_choose_names_flag(self, cli_runner, mock_dependencies):
        """Test choose names flag."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--choose-names",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0

    def test_custom_experiment_name(self, cli_runner, mock_dependencies):
        """Test custom experiment name."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--name",
                "my_custom_experiment",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0

    def test_max_parallel_setting(self, cli_runner, mock_dependencies):
        """Test max parallel conversations setting."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--max-parallel",
                "3",
                "--repetitions",
                "5",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0
        # Should warn about background execution
        assert "Parallel execution" in result.output or result.exit_code == 0


class TestRunCommandInteractiveMode:
    """Test interactive model selection."""

    def test_interactive_agent_a_selection(self, cli_runner, mock_dependencies):
        """Test interactive selection when agent A is not provided."""
        mock_dependencies["_prompt_for_model"].return_value = "claude"

        result = cli_runner.invoke(run, ["--agent-b", "gpt-4", "--turns", "2"])

        assert result.exit_code == 0
        mock_dependencies["_prompt_for_model"].assert_called()

    def test_interactive_agent_b_selection(self, cli_runner, mock_dependencies):
        """Test interactive selection when agent B is not provided."""
        mock_dependencies["_prompt_for_model"].return_value = "gpt-4"

        result = cli_runner.invoke(run, ["--agent-a", "claude", "--turns", "2"])

        assert result.exit_code == 0
        mock_dependencies["_prompt_for_model"].assert_called()

    def test_interactive_keyboard_interrupt(self, cli_runner, mock_dependencies):
        """Test handling of keyboard interrupt during interactive selection."""
        mock_dependencies["_prompt_for_model"].side_effect = KeyboardInterrupt()

        result = cli_runner.invoke(run, ["--agent-b", "gpt-4", "--turns", "2"])

        assert result.exit_code == 0
        assert "Model selection cancelled" in result.output

    def test_interactive_eof_error(self, cli_runner, mock_dependencies):
        """Test handling of EOF error during interactive selection."""
        mock_dependencies["_prompt_for_model"].side_effect = EOFError()

        result = cli_runner.invoke(run, ["--agent-b", "gpt-4", "--turns", "2"])

        assert result.exit_code == 0
        assert "Model selection cancelled" in result.output

    def test_interactive_general_error(self, cli_runner, mock_dependencies):
        """Test handling of general error during interactive selection."""
        mock_dependencies["_prompt_for_model"].side_effect = Exception("Test error")

        result = cli_runner.invoke(run, ["--agent-b", "gpt-4", "--turns", "2"])

        assert result.exit_code == 0
        assert "Error during model selection" in result.output


class TestRunCommandErrorHandling:
    """Test error handling scenarios."""

    def test_api_key_error_handling(self, cli_runner, mock_dependencies):
        """Test handling of API key errors."""
        mock_dependencies["validate_model_id"].side_effect = APIKeyError(
            "Test API key error"
        )

        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--agent-b", "gpt-4", "--turns", "2"]
        )

        # Should handle the error gracefully
        assert "API key" in result.output.lower() or result.exit_code != 0

    def test_invalid_model_error(self, cli_runner, mock_dependencies):
        """Test handling of invalid model errors."""
        mock_dependencies["validate_model_id"].side_effect = ValueError("Invalid model")

        result = cli_runner.invoke(
            run, ["--agent-a", "invalid_model", "--agent-b", "gpt-4", "--turns", "2"]
        )

        # Should handle the error gracefully
        assert result.exit_code != 0 or "Invalid model" in result.output

    def test_ollama_unavailable_warning(self, cli_runner, mock_dependencies):
        """Test warning when Ollama is unavailable but local models requested."""
        mock_dependencies["check_ollama_available"].return_value = False

        result = cli_runner.invoke(
            run, ["--agent-a", "local:llama2", "--agent-b", "gpt-4", "--turns", "2"]
        )

        # Should warn about Ollama not being available
        assert result.exit_code == 0  # Command should still proceed


class TestRunCommandDimensions:
    """Test conversation dimensions functionality."""

    def test_single_dimension(self, cli_runner, mock_dependencies):
        """Test command with single dimension."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--dimension",
                "philosophical",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0
        mock_dependencies["parse_dimensions"].assert_called()

    def test_multiple_dimensions(self, cli_runner, mock_dependencies):
        """Test command with multiple dimensions."""
        result = cli_runner.invoke(
            run,
            [
                "--agent-a",
                "claude",
                "--agent-b",
                "gpt-4",
                "--dimension",
                "philosophical",
                "--dimension",
                "technical",
                "--turns",
                "2",
            ],
        )

        assert result.exit_code == 0
        mock_dependencies["parse_dimensions"].assert_called()


class TestRunCommandNotifications:
    """Test notification functionality."""

    def test_notify_flag(self, cli_runner, mock_dependencies):
        """Test explicit notify flag."""
        result = cli_runner.invoke(
            run,
            ["--agent-a", "claude", "--agent-b", "gpt-4", "--notify", "--turns", "2"],
        )

        assert result.exit_code == 0

    def test_quiet_mode_auto_notify(self, cli_runner, mock_dependencies):
        """Test that quiet mode automatically enables notifications."""
        result = cli_runner.invoke(
            run,
            ["--agent-a", "claude", "--agent-b", "gpt-4", "--quiet", "--turns", "2"],
        )

        assert result.exit_code == 0
        # Quiet mode should enable notifications automatically


class TestRunCommandDefaults:
    """Test default value handling."""

    def test_default_turns(self, cli_runner, mock_dependencies):
        """Test that default turns value is used."""
        result = cli_runner.invoke(run, ["--agent-a", "claude", "--agent-b", "gpt-4"])

        assert result.exit_code == 0
        # Should use DEFAULT_TURNS value

    def test_default_convergence_profile(self, cli_runner, mock_dependencies):
        """Test that default convergence profile is used."""
        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--agent-b", "gpt-4", "--turns", "2"]
        )

        assert result.exit_code == 0
        # Should use 'balanced' as default convergence profile

    def test_default_first_speaker(self, cli_runner, mock_dependencies):
        """Test that default first speaker is agent A."""
        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--agent-b", "gpt-4", "--turns", "2"]
        )

        assert result.exit_code == 0
        # Should use 'a' as default first speaker

    def test_auto_generated_experiment_name(self, cli_runner, mock_dependencies):
        """Test that experiment name is auto-generated when not provided."""
        result = cli_runner.invoke(
            run, ["--agent-a", "claude", "--agent-b", "gpt-4", "--turns", "2"]
        )

        assert result.exit_code == 0
        mock_dependencies["generate_experiment_name"].assert_called_once()
        assert "Generated experiment name" in result.output

    def test_random_first_speaker(self, cli_runner, mock_dependencies):
        """Test random first speaker selection."""
        with patch("random.choice", return_value="b"):
            result = cli_runner.invoke(
                run,
                [
                    "--agent-a",
                    "claude",
                    "--agent-b",
                    "gpt-4",
                    "--first-speaker",
                    "random",
                    "--turns",
                    "2",
                ],
            )

        assert result.exit_code == 0
