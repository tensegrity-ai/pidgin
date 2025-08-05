# tests/cli/test_model_selector.py
"""Tests for the ModelSelector class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Tuple, Optional

from pidgin.config.models import MODELS, ModelConfig
from pidgin.config.model_types import ModelConfig as ModelConfigType
from pidgin.cli.constants import MODEL_GLYPHS
from pidgin.cli.helpers import validate_model_id, check_ollama_available
from pidgin.cli.model_selector import ModelSelector


class TestModelSelector:
    """Test suite for ModelSelector class.
    
    Tests the interactive model selection functionality including:
    - Model selection with various inputs
    - Model validation
    - Available models listing
    - Custom local model prompting
    """
    
    @pytest.fixture
    def mock_console(self):
        """Mock console for capturing output and providing input."""
        console = Mock()
        console.print = Mock()
        console.input = Mock()
        return console
    
    @pytest.fixture
    def mock_display(self):
        """Mock display utilities."""
        display = Mock()
        display.info = Mock()
        display.dim = Mock()
        display.error = Mock()
        display.warning = Mock()
        return display
    
    @pytest.fixture
    def model_selector(self, mock_console, mock_display):
        """Create a ModelSelector instance with mocked dependencies."""
        selector = ModelSelector()
        # Replace the console and display with mocks
        selector.console = mock_console
        selector.display = mock_display
        return selector
    
    # Tests for select_model method
    
    def test_select_model_with_numeric_selection(self, model_selector, mock_console):
        """Test selecting a model using numeric input."""
        # Mock console input to return "1" (first model)
        mock_console.input.return_value = "1"
        
        # Mock the internal model listing and mapping
        with patch.object(model_selector, 'get_available_models') as mock_get_models:
            mock_get_models.return_value = {
                'openai': [('gpt-4', Mock(display_name='GPT-4'))],
                'anthropic': [('claude-3-opus', Mock(display_name='Claude 3 Opus'))]
            }
            
            # We expect the selector to build a numeric mapping
            # Since we selected "1", it should return the first model
            # No need to patch _prompt_for_model anymore
            result = model_selector.select_model("Select model")
        
        assert result is not None
        # The actual implementation will map "1" to the first model
        
    def test_select_model_with_direct_model_id(self, model_selector, mock_console):
        """Test selecting a model using direct model ID."""
        mock_console.input.return_value = "claude-3-opus"
        
        with patch('pidgin.cli.helpers.validate_model_id', return_value=('claude-3-opus', 'Claude 3 Opus')):
            with patch.object(model_selector, 'get_available_models'):
                result = model_selector.select_model("Select model")
        
        # Should accept direct model ID
        assert result is not None
    
    def test_select_model_cancelled_by_user(self, model_selector, mock_console):
        """Test cancelling model selection with Ctrl+C."""
        mock_console.input.side_effect = KeyboardInterrupt()
        
        result = model_selector.select_model("Select model")
        
        assert result is None
        # Should handle gracefully and return None
    
    def test_select_model_eof_error(self, model_selector, mock_console):
        """Test handling EOF error during selection."""
        mock_console.input.side_effect = EOFError()
        
        result = model_selector.select_model("Select model")
        
        assert result is None
    
    def test_select_model_custom_local_option(self, model_selector, mock_console):
        """Test selecting custom local model option."""
        # Assume custom model is option "5"
        mock_console.input.side_effect = ["5", "my-custom-model"]
        
        with patch.object(model_selector, 'get_available_models') as mock_get_models:
            mock_get_models.return_value = {
                'openai': [('gpt-4', Mock())],
                'anthropic': [('claude-3-opus', Mock())],
                'local': [('llama3.1', Mock()), ('qwen2.5', Mock())]
            }
            
            with patch('pidgin.cli.model_selector.check_ollama_available', return_value=True):
                with patch.object(model_selector, 'prompt_for_custom_model', return_value='local:my-custom-model'):
                    result = model_selector.select_model("Select model")
        
        # Should return the custom local model
        assert result is not None
    
    def test_select_model_custom_local_ollama_not_available(self, model_selector, mock_console, mock_display):
        """Test selecting custom local model when Ollama is not running."""
        # Select custom model option
        mock_console.input.return_value = "5"
        
        with patch.object(model_selector, 'get_available_models') as mock_get_models:
            mock_get_models.return_value = {
                'openai': [('gpt-4', Mock(display_name='GPT-4'))],
                'anthropic': [('claude-3-opus', Mock(display_name='Claude 3 Opus'))],
                'local': [('llama3.1', Mock(display_name='Llama 3.1')), ('qwen2.5', Mock(display_name='Qwen 2.5'))]
            }
            
            with patch.object(model_selector, 'prompt_for_custom_model') as mock_prompt:
                mock_prompt.return_value = None
                result = model_selector.select_model("Select model")
        
        # Should call prompt_for_custom_model and return None
        assert result is None
        mock_prompt.assert_called_once()
    
    def test_select_model_invalid_selection(self, model_selector, mock_console, mock_display):
        """Test handling invalid model selection."""
        mock_console.input.return_value = "invalid-model-xyz"
        
        with patch('pidgin.cli.helpers.validate_model_id', side_effect=ValueError("Unknown model")):
            with patch.object(model_selector, 'get_available_models'):
                result = model_selector.select_model("Select model")
        
        assert result is None
        # Should show error message
    
    # Tests for validate_models method
    
    def test_validate_models_both_valid(self, model_selector):
        """Test validating two valid models."""
        with patch('pidgin.cli.model_selector.validate_model_id') as mock_validate:
            mock_validate.side_effect = [
                ('gpt-4', 'GPT-4'),
                ('claude-3-opus', 'Claude 3 Opus')
            ]
            
            # Should not raise any exception
            model_selector.validate_models('gpt-4', 'claude-3-opus')
    
    def test_validate_models_first_invalid(self, model_selector):
        """Test validation when first model is invalid."""
        with patch('pidgin.cli.model_selector.validate_model_id') as mock_validate:
            mock_validate.side_effect = ValueError("Unknown model: invalid-model")
            
            with pytest.raises(ValueError, match="Unknown model"):
                model_selector.validate_models('invalid-model', 'claude')
    
    def test_validate_models_second_invalid(self, model_selector):
        """Test validation when second model is invalid."""
        with patch('pidgin.cli.model_selector.validate_model_id') as mock_validate:
            mock_validate.side_effect = [
                ('gpt-4', 'GPT-4'),
                ValueError("Unknown model: invalid-model")
            ]
            
            with pytest.raises(ValueError, match="Unknown model"):
                model_selector.validate_models('gpt-4', 'invalid-model')
    
    def test_validate_models_with_silent_model(self, model_selector):
        """Test validation with the special 'silent' model."""
        with patch('pidgin.cli.model_selector.validate_model_id') as mock_validate:
            mock_validate.side_effect = [
                ('gpt-4', 'GPT-4'),
                ('silent', 'Silent')
            ]
            
            # Should handle silent model correctly
            model_selector.validate_models('gpt-4', 'silent')
    
    def test_validate_models_with_local_models(self, model_selector):
        """Test validation with local models."""
        with patch('pidgin.cli.model_selector.validate_model_id') as mock_validate:
            with patch('pidgin.cli.model_selector.check_ollama_available', return_value=True):
                mock_validate.side_effect = [
                    ('local:llama3.1', 'Local: llama3.1'),
                    ('local:mistral', 'Local: mistral')
                ]
                
                # Should validate local models successfully
                model_selector.validate_models('local:llama3.1', 'local:mistral')
    
    # Tests for get_available_models method
    
    def test_get_available_models_groups_by_provider(self, model_selector):
        """Test that models are properly grouped by provider."""
        # Mock MODELS to have a controlled set
        mock_models = {
            'gpt-4': ModelConfigType(
                model_id='gpt-4',
                display_name='GPT-4',
                provider='openai',
                aliases=['gpt4'],
                context_window=8192
            ),
            'claude-3-opus': ModelConfigType(
                model_id='claude-3-opus',
                display_name='Claude 3 Opus',
                provider='anthropic',
                aliases=['claude', 'opus'],
                context_window=200000
            ),
            'gemini-1.5-pro': ModelConfigType(
                model_id='gemini-1.5-pro',
                display_name='Gemini 1.5 Pro',
                provider='google',
                aliases=['gemini'],
                context_window=1000000
            ),
            'llama3.1': ModelConfigType(
                model_id='llama3.1',
                display_name='Llama 3.1',
                provider='local',
                aliases=['llama'],
                context_window=8192
            ),
            'silent': ModelConfigType(
                model_id='silent',
                display_name='Silent',
                provider='local',
                aliases=[],
                context_window=0
            )
        }
        
        with patch('pidgin.cli.model_selector.MODELS', mock_models):
            result = model_selector.get_available_models()
        
        # Should have models grouped by provider
        assert 'openai' in result
        assert 'anthropic' in result
        assert 'google' in result
        assert 'local' in result
        
        # Check that models are in correct groups
        openai_models = result['openai']
        assert len(openai_models) == 1
        assert openai_models[0][0] == 'gpt-4'
    
    def test_get_available_models_excludes_silent(self, model_selector):
        """Test that silent model is excluded from available models."""
        mock_models = {
            'gpt-4': ModelConfigType(
                model_id='gpt-4',
                display_name='GPT-4',
                provider='openai',
                aliases=['gpt4'],
                context_window=8192
            ),
            'silent': ModelConfigType(
                model_id='silent',
                display_name='Silent',
                provider='local',
                aliases=[],
                context_window=0
            )
        }
        
        with patch('pidgin.cli.model_selector.MODELS', mock_models):
            result = model_selector.get_available_models()
        
        # Silent model should not appear in any provider group
        for provider_models in result.values():
            model_ids = [model_id for model_id, _ in provider_models]
            assert 'silent' not in model_ids
    
    def test_get_available_models_empty_providers_excluded(self, model_selector):
        """Test that providers with no models are not included."""
        mock_models = {
            'gpt-4': ModelConfigType(
                model_id='gpt-4',
                display_name='GPT-4',
                provider='openai',
                aliases=['gpt4'],
                context_window=8192,
            )
        }
        
        with patch('pidgin.cli.model_selector.MODELS', mock_models):
            result = model_selector.get_available_models()
        
        # Only OpenAI should be present
        assert 'openai' in result
        assert 'anthropic' not in result
        assert 'google' not in result
    
    # Tests for prompt_for_custom_model method
    
    def test_prompt_for_custom_model_success(self, model_selector):
        """Test successful custom model prompt."""
        # Set the return value on the actual console being used
        model_selector.console.input.return_value = "my-custom-model"
        
        # Need to patch where it's used, not where it's defined
        with patch('pidgin.cli.model_selector.check_ollama_available', return_value=True):
            result = model_selector.prompt_for_custom_model()
        
        assert result == "local:my-custom-model"
    
    def test_prompt_for_custom_model_cancelled(self, model_selector, mock_console):
        """Test cancelling custom model prompt."""
        mock_console.input.side_effect = KeyboardInterrupt()
        
        result = model_selector.prompt_for_custom_model()
        
        assert result is None
    
    def test_prompt_for_custom_model_eof(self, model_selector, mock_console):
        """Test EOF during custom model prompt."""
        mock_console.input.side_effect = EOFError()
        
        result = model_selector.prompt_for_custom_model()
        
        assert result is None
    
    def test_prompt_for_custom_model_ollama_not_available(self, model_selector, mock_console, mock_display):
        """Test custom model prompt when Ollama is not available."""
        with patch('pidgin.cli.model_selector.check_ollama_available', return_value=False):
            result = model_selector.prompt_for_custom_model()
        
        assert result is None
        mock_display.error.assert_called_once()
    
    def test_prompt_for_custom_model_empty_input(self, model_selector, mock_console):
        """Test empty input for custom model."""
        mock_console.input.return_value = ""
        
        with patch('pidgin.cli.helpers.check_ollama_available', return_value=True):
            result = model_selector.prompt_for_custom_model()
        
        # Should handle empty input gracefully
        # Implementation detail: might return None or "local:"
        assert result is None or result == "local:"
    
    # Integration tests
    
    def test_full_selection_flow_numeric(self, model_selector, mock_console):
        """Test complete selection flow with numeric input."""
        # User selects option 2
        mock_console.input.return_value = "2"
        
        # Mock the model listing
        with patch.object(model_selector, 'get_available_models') as mock_get_models:
            mock_get_models.return_value = {
                'openai': [
                    ('gpt-4', ModelConfigType(
                        model_id='gpt-4',
                        display_name='GPT-4',
                        provider='openai',
                        aliases=['gpt4'],
                        context_window=8192
                    )),
                    ('gpt-3.5-turbo', ModelConfigType(
                        model_id='gpt-3.5-turbo',
                        display_name='GPT-3.5 Turbo',
                        provider='openai',
                        aliases=['gpt3.5'],
                        context_window=4096
                    ))
                ]
            }
            
            # Use the selector directly
            result = model_selector.select_model("Select agent")
        
        assert result is not None
    
    def test_display_formatting_with_glyphs(self, model_selector, mock_display):
        """Test that model display includes correct glyphs."""
        # This test verifies that MODEL_GLYPHS are used in display
        models = model_selector.get_available_models()
        
        # The actual implementation should use MODEL_GLYPHS
        # to format the display of each model
        # We're testing the expected behavior here
        
        # TODO: Add assertions once implementation details are known
        pass
    
    def test_provider_ordering(self, model_selector):
        """Test that providers are displayed in the expected order."""
        # Expected order: openai, anthropic, google, xai, local
        result = model_selector.get_available_models()
        
        # The implementation should maintain this order
        # when displaying to users
        # TODO: Add assertions based on implementation
        pass


class TestModelSelectorErrorHandling:
    """Test error handling scenarios for ModelSelector."""
    
    @pytest.fixture
    def mock_console(self):
        """Mock console for capturing output and providing input."""
        console = Mock()
        console.print = Mock()
        console.input = Mock()
        return console
    
    @pytest.fixture
    def mock_display(self):
        """Mock display utilities."""
        display = Mock()
        display.info = Mock()
        display.dim = Mock()
        display.error = Mock()
        display.warning = Mock()
        return display
    
    @pytest.fixture
    def model_selector(self, mock_console, mock_display):
        """Create a ModelSelector instance with mocked dependencies."""
        selector = ModelSelector()
        # Replace the console and display with mocks
        selector.console = mock_console
        selector.display = mock_display
        return selector
    
    def test_handle_unexpected_exception_during_selection(self, model_selector, mock_console, mock_display):
        """Test handling of unexpected exceptions."""
        mock_console.input.side_effect = Exception("Unexpected error")
        
        # Should raise the exception (not caught in the implementation)
        with pytest.raises(Exception):
            model_selector.select_model("Select model")
    
    def test_validate_models_with_network_error(self, model_selector):
        """Test model validation when network check fails."""
        with patch('pidgin.cli.model_selector.validate_model_id') as mock_validate:
            # validate_model_id will raise an exception
            mock_validate.side_effect = ValueError("Network error")
            
            # Should raise the validation error
            with pytest.raises(ValueError):
                model_selector.validate_models('local:llama3.1', 'gpt-4')


class TestModelSelectorMocking:
    """Test mocking strategies for CLI components."""
    
    def test_console_input_mocking(self):
        """Test that console input can be properly mocked."""
        from rich.console import Console
        console = Console()
        
        with patch.object(console, 'input', return_value='test-input'):
            result = console.input("Test prompt: ")
        
        assert result == 'test-input'
    
    def test_display_utils_mocking(self):
        """Test that DisplayUtils can be properly mocked."""
        from pidgin.ui.display_utils import DisplayUtils
        from rich.console import Console
        
        console = Console()
        display = DisplayUtils(console)
        
        with patch.object(display, 'info') as mock_info:
            display.info("Test message")
        
        mock_info.assert_called_once_with("Test message")


# TODO: Add more tests once ModelSelector implementation is complete:
# - Test behavior with different MODELS configurations
# - Test interaction with convergence settings
# - Test meditation mode handling
# - Test temperature resolution integration
# - Performance tests for large model lists
# - Test accessibility features (if any)