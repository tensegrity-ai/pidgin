"""Tests for LocalProvider class."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pidgin.core.types import Message
from pidgin.providers.local import LOCAL_MODELS, LocalProvider


@pytest.fixture
def mock_messages():
    """Create mock messages for testing."""
    return [
        Mock(spec=Message, role="user", content="Hello, test model!"),
        Mock(spec=Message, role="assistant", content="Hello! I'm here to help."),
    ]


class TestLocalProvider:
    """Test LocalProvider functionality."""

    def test_init_default(self):
        """Test initialization with default model name."""
        provider = LocalProvider()
        assert provider.model_name == "test"

    def test_init_custom_model(self):
        """Test initialization with custom model name."""
        provider = LocalProvider(model_name="custom")
        assert provider.model_name == "custom"

    @pytest.mark.asyncio
    async def test_stream_response_valid_model(self, mock_messages):
        """Test streaming response with valid test model."""
        provider = LocalProvider(model_name="test")

        # Mock the LocalTestModel
        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="This is a test response")

            # Collect response chunks
            chunks = []
            async for chunk in provider.stream_response(mock_messages, temperature=0.7):
                chunks.append(chunk)

            # Verify behavior
            assert chunks == ["This ", "is ", "a ", "test ", "response "]
            mock_model.generate.assert_called_once_with(mock_messages, 0.7)

    @pytest.mark.asyncio
    async def test_stream_response_invalid_model(self, mock_messages):
        """Test streaming response with invalid model name."""
        provider = LocalProvider(model_name="invalid")

        # Collect response chunks
        chunks = []
        async for chunk in provider.stream_response(mock_messages):
            chunks.append(chunk)

        # Should return error message
        assert len(chunks) == 1
        assert (
            chunks[0] == "Error: LocalProvider only supports 'test' model. Got: invalid"
        )

    @pytest.mark.asyncio
    async def test_stream_response_no_temperature(self, mock_messages):
        """Test streaming response without temperature parameter."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="Hello world")

            # Collect response chunks
            chunks = []
            async for chunk in provider.stream_response(mock_messages):
                chunks.append(chunk)

            # Verify behavior
            assert chunks == ["Hello ", "world "]
            mock_model.generate.assert_called_once_with(mock_messages, None)

    @pytest.mark.asyncio
    async def test_stream_response_single_word(self, mock_messages):
        """Test streaming response with single word."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="Yes")

            # Collect response chunks
            chunks = []
            async for chunk in provider.stream_response(mock_messages):
                chunks.append(chunk)

            # Verify behavior
            assert chunks == ["Yes "]

    @pytest.mark.asyncio
    async def test_stream_response_empty_response(self, mock_messages):
        """Test streaming response with empty response."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="")

            # Collect response chunks
            chunks = []
            async for chunk in provider.stream_response(mock_messages):
                chunks.append(chunk)

            # Should yield nothing for empty response
            assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_response_multiline(self, mock_messages):
        """Test streaming response with multiline text."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="Line one\nLine two")

            # Collect response chunks
            chunks = []
            async for chunk in provider.stream_response(mock_messages):
                chunks.append(chunk)

            # Should split on words, not lines
            assert chunks == ["Line ", "one ", "Line ", "two "]

    @pytest.mark.asyncio
    async def test_stream_response_timing(self, mock_messages):
        """Test that streaming has delays between chunks."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="Quick test")

            # Track timing
            start_time = asyncio.get_event_loop().time()
            chunks = []

            async for chunk in provider.stream_response(mock_messages):
                chunks.append(chunk)

            end_time = asyncio.get_event_loop().time()
            elapsed = end_time - start_time

            # Should have some delay (at least 0.01s per word)
            assert elapsed >= 0.01  # At least one delay
            assert chunks == ["Quick ", "test "]

    @pytest.mark.asyncio
    async def test_cleanup_default(self):
        """Test cleanup method (should use default implementation)."""
        provider = LocalProvider()

        # Should not raise any errors
        await provider.cleanup()

    def test_get_last_usage_default(self):
        """Test get_last_usage method (should return None)."""
        provider = LocalProvider()

        # Should return None (default implementation)
        usage = provider.get_last_usage()
        assert usage is None

    @pytest.mark.asyncio
    async def test_stream_response_with_special_characters(self, mock_messages):
        """Test streaming response with special characters."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(return_value="Hello! How's it going? 😊")

            # Collect response chunks
            chunks = []
            async for chunk in provider.stream_response(mock_messages):
                chunks.append(chunk)

            # Should handle special characters correctly
            assert chunks == ["Hello! ", "How's ", "it ", "going? ", "😊 "]

    @pytest.mark.asyncio
    async def test_model_import_error_handling(self, mock_messages):
        """Test handling of import errors for LocalTestModel."""
        provider = LocalProvider()

        # Mock import error
        with patch(
            "pidgin.providers.test_model.LocalTestModel",
            side_effect=ImportError("Module not found"),
        ):
            # Should raise the import error
            with pytest.raises(ImportError, match="Module not found"):
                async for _ in provider.stream_response(mock_messages):
                    pass

    @pytest.mark.asyncio
    async def test_model_generation_error_handling(self, mock_messages):
        """Test handling of errors during model generation."""
        provider = LocalProvider()

        with patch("pidgin.providers.test_model.LocalTestModel") as mock_model_class:
            mock_model = mock_model_class.return_value
            mock_model.generate = AsyncMock(side_effect=Exception("Generation failed"))

            # Should propagate the exception
            with pytest.raises(Exception, match="Generation failed"):
                async for _ in provider.stream_response(mock_messages):
                    pass


class TestLocalModels:
    """Test LOCAL_MODELS configuration."""

    def test_local_test_model_config(self):
        """Test that local:test model is properly configured."""
        assert "local:test" in LOCAL_MODELS

        config = LOCAL_MODELS["local:test"]
        assert config.model_id == "local:test"
        assert config.display_name == "Test"
        assert config.aliases == ["test", "local-test"]
        assert config.provider == "local"
        assert config.context_window == 8192
        assert config.notes == "Deterministic test model for offline development"

    def test_local_models_structure(self):
        """Test that LOCAL_MODELS has expected structure."""
        assert isinstance(LOCAL_MODELS, dict)
        assert len(LOCAL_MODELS) == 1  # Currently only test model

        # All values should be ModelConfig instances
        for model_id, config in LOCAL_MODELS.items():
            assert hasattr(config, "model_id")
            assert hasattr(config, "provider")
            assert hasattr(config, "display_name")
            assert hasattr(config, "aliases")
            assert hasattr(config, "context_window")
