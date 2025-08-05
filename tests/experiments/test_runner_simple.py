"""Tests for ExperimentRunner class (simplified to avoid import issues)."""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Mock database and aiohttp modules to avoid import issues
sys.modules["duckdb"] = MagicMock()
sys.modules["duckdb.duckdb"] = MagicMock()
sys.modules["duckdb.duckdb.functional"] = MagicMock()
sys.modules["aiohttp"] = MagicMock()


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_experiment_config():
    """Create a sample experiment configuration."""
    from pidgin.experiments.config import ExperimentConfig

    return ExperimentConfig(
        name="Test Experiment",
        agent_a_model="gpt-4",
        agent_b_model="claude-3",
        repetitions=2,
        max_turns=5,
        temperature_a=0.7,
        temperature_b=0.8,
        custom_prompt="Test prompt",
        max_parallel=2,
        allow_truncation=False,  # Add allow_truncation field
    )


@pytest.fixture
def mock_daemon():
    """Create a mock daemon."""
    daemon = Mock()
    daemon.is_stopping.return_value = False
    return daemon


class TestExperimentRunnerBasic:
    """Test ExperimentRunner basic functionality."""

    def test_init(self, temp_output_dir, mock_daemon):
        """Test ExperimentRunner initialization."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir, daemon=mock_daemon)

        assert runner.output_dir == temp_output_dir
        assert runner.daemon == mock_daemon
        assert runner.active_tasks == {}
        assert runner.completed_count == 0
        assert runner.failed_count == 0
        assert runner.console is not None
        assert runner.display is not None

    def test_init_without_daemon(self, temp_output_dir):
        """Test ExperimentRunner initialization without daemon."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)

        assert runner.output_dir == temp_output_dir
        assert runner.daemon is None
        assert runner.active_tasks == {}

    def test_register_conversation(self, temp_output_dir):
        """Test conversation registration in manifest."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)
        exp_dir = temp_output_dir / "test_exp"
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest file
        manifest_path = exp_dir / "manifest.json"
        manifest_data = {"experiment_id": "test_exp", "conversations": {}}
        import json

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        with patch("pidgin.experiments.conversation_orchestrator.ManifestManager") as mock_manifest_class:
            mock_manifest = Mock()
            mock_manifest_class.return_value = mock_manifest

            # Use the orchestrator to register conversation
            runner.orchestrator.register_conversation(exp_dir, "conv_123")

            mock_manifest_class.assert_called_once_with(exp_dir)
            mock_manifest.add_conversation.assert_called_once_with("conv_123", "conv_123.jsonl")

    @pytest.mark.asyncio
    async def test_setup_event_bus(self, temp_output_dir):
        """Test event bus setup."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)
        exp_dir = temp_output_dir / "test_exp"
        exp_dir.mkdir(parents=True, exist_ok=True)

        with patch("pidgin.experiments.experiment_setup.TrackingEventBus") as mock_bus_class:
            mock_bus = AsyncMock()
            mock_bus_class.return_value = mock_bus

            result = await runner.setup.setup_event_bus(exp_dir, "conv_123")

            assert result == mock_bus
            mock_bus_class.assert_called_once_with(
                experiment_dir=exp_dir, conversation_id="conv_123"
            )
            mock_bus.start.assert_called_once()

    def test_setup_output_and_console_chat_mode(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test output and console setup in chat mode."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)
        exp_dir = temp_output_dir / "test_exp"
        exp_dir.mkdir(parents=True, exist_ok=True)

        sample_experiment_config.display_mode = "chat"

        with patch("pidgin.io.output_manager.OutputManager") as mock_output_class:
            mock_output = Mock()
            mock_output_class.return_value = mock_output

            output, console = runner.setup.setup_output_and_console(
                sample_experiment_config, exp_dir, "conv_123"
            )

            assert output == mock_output
            assert console is not None  # Console created for chat mode

            # Test that create_conversation_dir is overridden
            result = output.create_conversation_dir("conv_123")
            assert result == ("conv_123", exp_dir)

    def test_setup_output_and_console_tail_mode(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test output and console setup in tail mode."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)
        exp_dir = temp_output_dir / "test_exp"
        exp_dir.mkdir(parents=True, exist_ok=True)

        sample_experiment_config.display_mode = "tail"

        with patch("pidgin.io.output_manager.OutputManager") as mock_output_class:
            mock_output = Mock()
            mock_output_class.return_value = mock_output

            output, console = runner.setup.setup_output_and_console(
                sample_experiment_config, exp_dir, "conv_123"
            )

            assert output == mock_output
            assert console is not None  # Console created for tail mode

    def test_setup_output_and_console_no_display(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test output and console setup with no display mode."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)
        exp_dir = temp_output_dir / "test_exp"
        exp_dir.mkdir(parents=True, exist_ok=True)

        sample_experiment_config.display_mode = "none"

        with patch("pidgin.io.output_manager.OutputManager") as mock_output_class:
            mock_output = Mock()
            mock_output_class.return_value = mock_output

            output, console = runner.setup.setup_output_and_console(
                sample_experiment_config, exp_dir, "conv_123"
            )

            assert output == mock_output
            assert console is None  # No console for 'none' display mode

    @pytest.mark.asyncio
    async def test_create_agents_and_providers_success(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test successful agent and provider creation."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)

        # Mock model configs
        mock_model_config = Mock()
        mock_model_config.model_id = "test-model-id"
        mock_model_config.provider = "test-provider"
        mock_model_config.display_name = "test-model"  # Use display_name instead of shortname

        with patch(
            "pidgin.experiments.experiment_setup.get_model_config", return_value=mock_model_config
        ), patch(
            "pidgin.experiments.experiment_setup.get_provider_for_model"
        ) as mock_get_provider:

            mock_provider = AsyncMock()
            mock_get_provider.return_value = mock_provider

            agents, providers = await runner.setup.create_agents_and_providers(
                sample_experiment_config
            )

            # Check agents
            assert "agent_a" in agents
            assert "agent_b" in agents
            assert agents["agent_a"].id == "agent_a"
            assert agents["agent_a"].model == "test-model-id"
            assert agents["agent_a"].temperature == 0.7
            assert agents["agent_b"].id == "agent_b"
            assert agents["agent_b"].model == "test-model-id"
            assert agents["agent_b"].temperature == 0.8

            # Check providers
            assert providers["agent_a"] == mock_provider
            assert providers["agent_b"] == mock_provider

            # Check provider creation calls
            assert mock_get_provider.call_count == 2

    @pytest.mark.asyncio
    async def test_create_agents_and_providers_invalid_config(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test agent creation with invalid model configuration."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)

        with patch("pidgin.experiments.experiment_setup.get_model_config", return_value=None):
            with pytest.raises(ValueError, match="Invalid model configuration"):
                await runner.setup.create_agents_and_providers(sample_experiment_config)

    @pytest.mark.asyncio
    async def test_create_agents_and_providers_provider_failure(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test agent creation when provider creation fails."""
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)

        mock_model_config = Mock()
        mock_model_config.model_id = "test-model-id"
        mock_model_config.provider = "test-provider"

        with patch(
            "pidgin.experiments.experiment_setup.get_model_config", return_value=mock_model_config
        ), patch("pidgin.experiments.experiment_setup.get_provider_for_model", return_value=None):

            with pytest.raises(ValueError, match="Failed to create providers"):
                await runner.setup.create_agents_and_providers(sample_experiment_config)

    @pytest.mark.asyncio
    async def test_run_parallel_conversations_with_daemon_stop(
        self, temp_output_dir, sample_experiment_config, mock_daemon
    ):
        """Test parallel conversation execution when daemon requests stop."""
        from pidgin.experiments.runner import ExperimentRunner

        mock_daemon.is_stopping.return_value = True
        runner = ExperimentRunner(temp_output_dir, daemon=mock_daemon)
        exp_dir = temp_output_dir / "test_exp"
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Set up daemon to stop immediately
        mock_daemon.stop_requested = True

        await runner._run_parallel_conversations(
            "test_exp", sample_experiment_config, exp_dir
        )

        # Should complete without running conversations
        assert runner.completed_count == 0
        assert runner.failed_count == 0

    @pytest.mark.asyncio
    async def test_create_and_run_conductor_basic(
        self, temp_output_dir, sample_experiment_config
    ):
        """Test conductor creation and running."""
        from pidgin.core.types import Agent
        from pidgin.experiments.runner import ExperimentRunner

        runner = ExperimentRunner(temp_output_dir)

        # Mock dependencies
        mock_agents = {"agent_a": Mock(spec=Agent), "agent_b": Mock(spec=Agent)}
        mock_providers = {"agent_a": AsyncMock(), "agent_b": AsyncMock()}
        mock_output = Mock()
        mock_console = Mock()
        mock_event_bus = AsyncMock()

        with patch(
            "pidgin.experiments.conversation_orchestrator.build_initial_prompt", return_value="Test prompt"
        ), patch("pidgin.experiments.conversation_orchestrator.Conductor") as mock_conductor_class:

            mock_conductor = AsyncMock()
            mock_conductor_class.return_value = mock_conductor

            await runner.orchestrator.create_and_run_conductor(
                config=sample_experiment_config,
                agents=mock_agents,
                providers=mock_providers,
                output_manager=mock_output,
                console=mock_console,
                event_bus=mock_event_bus,
                conversation_id="conv_123",
            )

            # Check conductor creation
            mock_conductor_class.assert_called_once_with(
                base_providers=mock_providers,
                output_manager=mock_output,
                console=mock_console,
                convergence_threshold_override=sample_experiment_config.convergence_threshold,
                convergence_action_override=sample_experiment_config.convergence_action,
                bus=mock_event_bus,
            )

            # Check conversation run
            mock_conductor.run_conversation.assert_called_once()
            call_args = mock_conductor.run_conversation.call_args
            # Should pass individual agents, not the dict
            assert call_args.kwargs["agent_a"] == mock_agents["agent_a"]
            assert call_args.kwargs["agent_b"] == mock_agents["agent_b"]
            assert call_args.kwargs["max_turns"] == 5
            assert call_args.kwargs["initial_prompt"] == "Test prompt"
            # first_speaker and daemon are not passed to conductor
