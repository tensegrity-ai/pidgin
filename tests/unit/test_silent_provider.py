"""Tests for SilentProvider."""

import pytest
from unittest.mock import Mock

from pidgin.providers.silent import SilentProvider, SILENT_MODELS
from pidgin.core.types import Message


class TestSilentModels:
    """Test SILENT_MODELS configuration."""
    
    def test_silent_models_structure(self):
        """Test that SILENT_MODELS has correct structure."""
        assert "silent" in SILENT_MODELS
        
        silent_model = SILENT_MODELS["silent"]
        assert silent_model.model_id == "silent"
        assert silent_model.shortname == "Silence"
        assert silent_model.provider == "silent"
        assert silent_model.context_window == 999999
        assert silent_model.pricing_tier == "free"
        
        # Test aliases
        assert "void" in silent_model.aliases
        assert "quiet" in silent_model.aliases
        assert "meditation" in silent_model.aliases
        
        # Test characteristics
        assert silent_model.characteristics.verbosity_level == 0
        assert silent_model.characteristics.avg_response_length == "short"
        assert silent_model.characteristics.conversation_style == "concise"
        
        # Test recommended pairings
        assert "claude-4-opus-20250514" in silent_model.characteristics.recommended_pairings
        assert "gpt-4.1" in silent_model.characteristics.recommended_pairings
        assert "o1" in silent_model.characteristics.recommended_pairings
        
        # Test notes
        assert "meditation mode" in silent_model.notes
    
    def test_silent_models_immutable(self):
        """Test that SILENT_MODELS is properly configured."""
        # Should be a dict with one key
        assert len(SILENT_MODELS) == 1
        assert isinstance(SILENT_MODELS, dict)


class TestSilentProvider:
    """Test SilentProvider class."""
    
    def test_init(self):
        """Test SilentProvider initialization."""
        provider = SilentProvider("silent")
        assert provider.model == "silent"
        
        # Test with different model name (should still work)
        provider2 = SilentProvider("any-model")
        assert provider2.model == "any-model"
    
    def test_init_with_different_models(self):
        """Test that initialization works with any model name."""
        test_models = ["silent", "void", "quiet", "meditation", "any-string"]
        
        for model in test_models:
            provider = SilentProvider(model)
            assert provider.model == model
    
    @pytest.mark.asyncio
    async def test_stream_response_basic(self):
        """Test basic stream_response functionality."""
        provider = SilentProvider("silent")
        
        messages = [
            Message(role="user", content="Hello", agent_id="agent_a"),
            Message(role="assistant", content="Hi there", agent_id="agent_b")
        ]
        
        response_parts = []
        async for part in provider.stream_response(messages):
            response_parts.append(part)
        
        # Should return exactly one empty string
        assert len(response_parts) == 1
        assert response_parts[0] == ""
    
    @pytest.mark.asyncio
    async def test_stream_response_with_temperature(self):
        """Test stream_response with temperature parameter."""
        provider = SilentProvider("silent")
        
        messages = [Message(role="user", content="Test", agent_id="agent_a")]
        
        response_parts = []
        async for part in provider.stream_response(messages, temperature=0.7):
            response_parts.append(part)
        
        # Should return exactly one empty string, ignoring temperature
        assert len(response_parts) == 1
        assert response_parts[0] == ""
    
    @pytest.mark.asyncio
    async def test_stream_response_with_none_temperature(self):
        """Test stream_response with None temperature."""
        provider = SilentProvider("silent")
        
        messages = [Message(role="user", content="Test", agent_id="agent_a")]
        
        response_parts = []
        async for part in provider.stream_response(messages, temperature=None):
            response_parts.append(part)
        
        # Should return exactly one empty string
        assert len(response_parts) == 1
        assert response_parts[0] == ""
    
    @pytest.mark.asyncio
    async def test_stream_response_ignores_messages(self):
        """Test that stream_response ignores message content."""
        provider = SilentProvider("silent")
        
        # Test with empty messages
        empty_messages = []
        response_parts = []
        async for part in provider.stream_response(empty_messages):
            response_parts.append(part)
        assert len(response_parts) == 1
        assert response_parts[0] == ""
        
        # Test with complex messages
        complex_messages = [
            Message(role="user", content="Very long message with lots of content", agent_id="agent_a"),
            Message(role="assistant", content="Another long response", agent_id="agent_b"),
            Message(role="user", content="More content here", agent_id="agent_a"),
        ]
        
        response_parts = []
        async for part in provider.stream_response(complex_messages):
            response_parts.append(part)
        
        # Should still return exactly one empty string
        assert len(response_parts) == 1
        assert response_parts[0] == ""
    
    @pytest.mark.asyncio
    async def test_stream_response_multiple_calls(self):
        """Test that multiple calls to stream_response work consistently."""
        provider = SilentProvider("silent")
        
        messages = [Message(role="user", content="Test", agent_id="agent_a")]
        
        # First call
        response_parts1 = []
        async for part in provider.stream_response(messages):
            response_parts1.append(part)
        
        # Second call
        response_parts2 = []
        async for part in provider.stream_response(messages, temperature=0.5):
            response_parts2.append(part)
        
        # Both should return the same result
        assert response_parts1 == response_parts2
        assert len(response_parts1) == 1
        assert response_parts1[0] == ""
    
    @pytest.mark.asyncio
    async def test_stream_response_is_generator(self):
        """Test that stream_response returns an async generator."""
        provider = SilentProvider("silent")
        
        messages = [Message(role="user", content="Test", agent_id="agent_a")]
        
        response_gen = provider.stream_response(messages)
        
        # Should be an async generator
        assert hasattr(response_gen, '__aiter__')
        assert hasattr(response_gen, '__anext__')
        
        # Should be able to iterate
        parts = [part async for part in response_gen]
        assert len(parts) == 1
        assert parts[0] == ""
    
    @pytest.mark.asyncio
    async def test_stream_response_with_different_model_names(self):
        """Test that stream_response works regardless of model name."""
        test_models = ["silent", "void", "quiet", "meditation", "any-name"]
        
        for model_name in test_models:
            provider = SilentProvider(model_name)
            
            messages = [Message(role="user", content="Test", agent_id="agent_a")]
            
            response_parts = []
            async for part in provider.stream_response(messages):
                response_parts.append(part)
            
            # Should always return exactly one empty string
            assert len(response_parts) == 1
            assert response_parts[0] == ""
    
    def test_provider_attributes(self):
        """Test that provider has correct attributes."""
        provider = SilentProvider("test-model")
        
        # Should have model attribute
        assert hasattr(provider, 'model')
        assert provider.model == "test-model"
        
        # Should have stream_response method
        assert hasattr(provider, 'stream_response')
        assert callable(provider.stream_response)
    
    @pytest.mark.asyncio
    async def test_stream_response_type_annotations(self):
        """Test that stream_response handles type annotations correctly."""
        provider = SilentProvider("silent")
        
        # Create messages with proper types
        messages = [
            Message(role="user", content="Hello", agent_id="agent_a"),
            Message(role="assistant", content="Hi", agent_id="agent_b")
        ]
        
        # Test with explicit temperature types
        response_parts = []
        async for part in provider.stream_response(messages, temperature=0.0):
            response_parts.append(part)
        
        assert len(response_parts) == 1
        assert response_parts[0] == ""
        assert isinstance(response_parts[0], str)


class TestSilentProviderIntegration:
    """Test SilentProvider integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_meditation_mode_simulation(self):
        """Test that SilentProvider simulates meditation mode correctly."""
        provider = SilentProvider("meditation")
        
        # Simulate a conversation where one agent is silent
        conversation = [
            Message(role="user", content="What do you think about this topic?", agent_id="agent_a"),
            Message(role="assistant", content="I think it's interesting because...", agent_id="agent_b"),
            Message(role="user", content="Do you agree?", agent_id="agent_a"),
        ]
        
        # Silent provider should respond with empty string
        response_parts = []
        async for part in provider.stream_response(conversation):
            response_parts.append(part)
        
        # Should represent silence
        assert len(response_parts) == 1
        assert response_parts[0] == ""
    
    @pytest.mark.asyncio
    async def test_provider_consistency(self):
        """Test that provider behaves consistently across different scenarios."""
        provider = SilentProvider("void")
        
        # Test with various message configurations
        test_scenarios = [
            [],  # Empty messages
            [Message(role="user", content="Single message", agent_id="agent_a")],
            [Message(role="user", content="", agent_id="agent_a"), Message(role="assistant", content="", agent_id="agent_b")],  # Empty content
            [Message(role="user", content="A" * 1000, agent_id="agent_a")],  # Very long message
        ]
        
        for messages in test_scenarios:
            response_parts = []
            async for part in provider.stream_response(messages):
                response_parts.append(part)
            
            # Should always return the same result
            assert len(response_parts) == 1
            assert response_parts[0] == ""
    
    def test_model_config_integration(self):
        """Test that SilentProvider works with its model configuration."""
        # Test that we can create provider with models from SILENT_MODELS
        for model_id in SILENT_MODELS.keys():
            provider = SilentProvider(model_id)
            assert provider.model == model_id
        
        # Test with model aliases
        silent_model = SILENT_MODELS["silent"]
        for alias in silent_model.aliases:
            provider = SilentProvider(alias)
            assert provider.model == alias
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test that SilentProvider handles edge cases gracefully."""
        provider = SilentProvider("silent")
        
        # Test with None messages (should not happen in practice but test robustness)
        try:
            response_parts = []
            async for part in provider.stream_response(None):
                response_parts.append(part)
            # If it doesn't crash, that's good
        except (TypeError, AttributeError):
            # Expected behavior for None input
            pass
        
        # Test with very unusual temperature values
        messages = [Message(role="user", content="Test", agent_id="agent_a")]
        
        unusual_temperatures = [-1.0, 2.0, 100.0, float('inf')]
        for temp in unusual_temperatures:
            response_parts = []
            async for part in provider.stream_response(messages, temperature=temp):
                response_parts.append(part)
            
            # Should still return empty string regardless of temperature
            assert len(response_parts) == 1
            assert response_parts[0] == ""