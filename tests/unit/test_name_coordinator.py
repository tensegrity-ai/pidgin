"""Test agent naming and name coordination logic."""

from unittest.mock import Mock, patch

import pytest

from pidgin.config.models import ModelConfig
from pidgin.core.name_coordinator import NameCoordinator
from pidgin.core.types import Agent


class TestNameCoordinator:
    """Test suite for NameCoordinator."""

    @pytest.fixture
    def coordinator(self):
        """Create a NameCoordinator instance."""
        return NameCoordinator()

    def test_initialization(self, coordinator):
        """Test coordinator initializes with correct defaults."""
        assert coordinator.choose_names_mode is False
        assert coordinator.agent_chosen_names == {}

    def test_initialize_name_mode(self, coordinator):
        """Test setting up name choosing mode."""
        coordinator.initialize_name_mode(True)
        assert coordinator.choose_names_mode is True
        assert coordinator.agent_chosen_names == {}

        coordinator.initialize_name_mode(False)
        assert coordinator.choose_names_mode is False
        assert coordinator.agent_chosen_names == {}

    @patch("pidgin.core.name_coordinator.get_model_config")
    def test_get_provider_name_with_config(self, mock_get_config, coordinator):
        """Test getting provider name when model config exists."""
        mock_config = Mock(spec=ModelConfig)
        mock_config.provider = "anthropic"
        mock_get_config.return_value = mock_config

        provider = coordinator.get_provider_name("claude-3-opus")
        assert provider == "anthropic"
        mock_get_config.assert_called_once_with("claude-3-opus")

    @patch("pidgin.core.name_coordinator.get_model_config")
    def test_get_provider_name_fallback_patterns(self, mock_get_config, coordinator):
        """Test provider name fallback pattern matching."""
        mock_get_config.return_value = None

        # Test Claude models
        assert coordinator.get_provider_name("claude-3-opus") == "anthropic"
        assert coordinator.get_provider_name("CLAUDE-instant") == "anthropic"

        # Test GPT models
        assert coordinator.get_provider_name("gpt-4") == "openai"
        assert coordinator.get_provider_name("GPT-3.5-turbo") == "openai"
        assert coordinator.get_provider_name("o1-preview") == "openai"

        # Test Gemini models
        assert coordinator.get_provider_name("gemini-pro") == "google"
        assert coordinator.get_provider_name("GEMINI-1.5") == "google"

        # Test Grok models
        assert coordinator.get_provider_name("grok-1") == "xai"
        assert coordinator.get_provider_name("GROK-beta") == "xai"

        # Test unknown model defaults to openai
        assert coordinator.get_provider_name("unknown-model") == "openai"

    def test_extract_chosen_name_patterns(self, coordinator):
        """Test extracting self-chosen names from various patterns."""
        # Test "I'll go by X" pattern
        assert coordinator.extract_chosen_name("I'll go by Alice") == "Alice"
        assert coordinator.extract_chosen_name("I'll go by [Bob]") == "Bob"

        # Test "Call me X" pattern
        assert coordinator.extract_chosen_name("Call me Charlie") == "Charlie"
        assert coordinator.extract_chosen_name("Call me [David]") == "David"

        # Test "I'll be X" pattern
        assert coordinator.extract_chosen_name("I'll be Echo") == "Echo"
        assert coordinator.extract_chosen_name("I'll be [Frank]") == "Frank"

        # Test "My name is X" pattern
        assert coordinator.extract_chosen_name("My name is Grace") == "Grace"
        assert coordinator.extract_chosen_name("My name is [Henry]") == "Henry"

        # Test "I choose X" pattern
        assert coordinator.extract_chosen_name("I choose Iris") == "Iris"
        assert coordinator.extract_chosen_name("I choose [Jack]") == "Jack"

        # Test "I am X" pattern
        assert coordinator.extract_chosen_name("I am Kate") == "Kate"
        assert coordinator.extract_chosen_name("I am [Leo]") == "Leo"

        # Test "[Name] here" pattern
        assert coordinator.extract_chosen_name("[Maya] here") == "Maya"
        assert coordinator.extract_chosen_name("Nova here, ready to chat") == "Nova"

    def test_extract_chosen_name_quoted(self, coordinator):
        """Test extracting quoted names."""
        assert coordinator.extract_chosen_name('You can call me "Otto"') == "Otto"
        assert coordinator.extract_chosen_name("I'll be 'Pam'") == "Pam"
        assert coordinator.extract_chosen_name('Call me "[Quinn]"') == "Quinn"

    def test_extract_chosen_name_bracketed_fallback(self, coordinator):
        """Test bracketed name extraction as fallback."""
        assert (
            coordinator.extract_chosen_name("Hi, I'm [Rex]. Nice to meet you!") == "Rex"
        )
        assert (
            coordinator.extract_chosen_name("Let's start. [Sam] reporting for duty.")
            == "Sam"
        )

    def test_extract_chosen_name_length_limit(self, coordinator):
        """Test that names must be 2-8 characters."""
        # Too short (1 char)
        assert coordinator.extract_chosen_name("I'll go by A") is None

        # The regex \w{2,8} will match the first 8 chars of longer names
        # This is actually the current behavior - it truncates to 8 chars
        assert coordinator.extract_chosen_name("I'll go by Verylongname") == "Verylong"

        # Just right (2-8 chars)
        assert coordinator.extract_chosen_name("I'll go by Bo") == "Bo"
        assert coordinator.extract_chosen_name("I'll go by Maxeight") == "Maxeight"

    def test_extract_chosen_name_no_match(self, coordinator):
        """Test when no name pattern is found."""
        assert coordinator.extract_chosen_name("Hello, how are you?") is None
        assert (
            coordinator.extract_chosen_name("I don't have a preference for names")
            is None
        )
        assert coordinator.extract_chosen_name("") is None

    def test_extract_chosen_name_case_insensitive(self, coordinator):
        """Test that name extraction is case insensitive."""
        assert coordinator.extract_chosen_name("I'LL GO BY alice") == "alice"
        assert coordinator.extract_chosen_name("CALL ME BOB") == "BOB"
        assert coordinator.extract_chosen_name("i am Charlie") == "Charlie"

    @patch("pidgin.core.name_coordinator.get_model_config")
    def test_assign_display_names_different_models(self, mock_get_config, coordinator):
        """Test assigning display names for different models."""
        # Create mock configs
        config_a = Mock(spec=ModelConfig)
        config_a.display_name = "claude"
        config_b = Mock(spec=ModelConfig)
        config_b.display_name = "gpt4"

        mock_get_config.side_effect = [config_a, config_b]

        # Create agents
        agent_a = Agent(id="agent_a", model="claude-3-opus")
        agent_b = Agent(id="agent_b", model="gpt-4")

        # Assign names
        coordinator.assign_display_names(agent_a, agent_b)

        # Check results
        assert agent_a.display_name == "claude"
        assert agent_b.display_name == "gpt4"
        assert agent_a.model_display_name == "claude"
        assert agent_b.model_display_name == "gpt4"

    @patch("pidgin.core.name_coordinator.get_model_config")
    def test_assign_display_names_same_model(self, mock_get_config, coordinator):
        """Test assigning display names for same model."""
        # Create mock config
        config = Mock(spec=ModelConfig)
        config.display_name = "gpt4"

        mock_get_config.side_effect = [config, config]

        # Create agents
        agent_a = Agent(id="agent_a", model="gpt-4")
        agent_b = Agent(id="agent_b", model="gpt-4")

        # Assign names
        coordinator.assign_display_names(agent_a, agent_b)

        # Check results - same model gets letters
        assert agent_a.display_name == "gpt4-A"
        assert agent_b.display_name == "gpt4-B"
        assert agent_a.model_display_name == "gpt4"
        assert agent_b.model_display_name == "gpt4"

    @patch("pidgin.core.name_coordinator.get_model_config")
    def test_assign_display_names_no_config(self, mock_get_config, coordinator):
        """Test assigning display names when no config exists."""
        mock_get_config.return_value = None

        # Create agents
        agent_a = Agent(id="agent_a", model="test-model-a")
        agent_b = Agent(id="agent_b", model="test-model-b")

        # Assign names
        coordinator.assign_display_names(agent_a, agent_b)

        # Check fallback names
        assert agent_a.display_name == "Agent A"
        assert agent_b.display_name == "Agent B"
        assert agent_a.model_display_name is None
        assert agent_b.model_display_name is None

    @patch("pidgin.core.name_coordinator.get_model_config")
    def test_assign_display_names_mixed_config(self, mock_get_config, coordinator):
        """Test when one agent has config and one doesn't."""
        config_a = Mock(spec=ModelConfig)
        config_a.display_name = "claude"

        mock_get_config.side_effect = [config_a, None]

        # Create agents
        agent_a = Agent(id="agent_a", model="claude-3-opus")
        agent_b = Agent(id="agent_b", model="unknown-model")

        # Assign names
        coordinator.assign_display_names(agent_a, agent_b)

        # Check fallback behavior when one config is missing
        assert agent_a.display_name == "Agent A"
        assert agent_b.display_name == "Agent B"
        assert agent_a.model_display_name is None
        assert agent_b.model_display_name is None
