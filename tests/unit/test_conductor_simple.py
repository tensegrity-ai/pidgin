"""Simple test to verify the conductor refactored example import fix."""

import pytest
from pidgin.providers.test_model import LocalTestModel
from pidgin.core.types import Message


class TestLocalTestModelFix:
    """Test that LocalTestModel works as expected for the conductor tests."""
    
    def test_local_test_model_instantiation(self):
        """Test that LocalTestModel can be instantiated with responses parameter."""
        # This is what the conductor tests expect to work
        provider = LocalTestModel(responses=["Response 1", "Response 2", "Response 3"])
        
        assert provider.custom_responses == ["Response 1", "Response 2", "Response 3"]
        assert provider.custom_response_index == 0
    
    def test_local_test_model_without_responses(self):
        """Test that LocalTestModel works without custom responses."""
        provider = LocalTestModel()
        
        assert provider.custom_responses is None
        assert hasattr(provider, 'responses')
        assert 'greetings' in provider.responses
    
    @pytest.mark.asyncio
    async def test_stream_response_with_custom_responses(self):
        """Test that stream_response works with custom responses."""
        provider = LocalTestModel(responses=["Custom response 1", "Custom response 2"])
        
        messages = [Message(role="user", content="Hello", agent_id="test")]
        
        # First call should return first response
        response_chunks = []
        async for chunk in provider.stream_response(messages):
            response_chunks.append(chunk)
        
        assert len(response_chunks) == 1
        assert response_chunks[0] == "Custom response 1"
        
        # Second call should return second response
        response_chunks = []
        async for chunk in provider.stream_response(messages):
            response_chunks.append(chunk)
        
        assert len(response_chunks) == 1
        assert response_chunks[0] == "Custom response 2"
        
        # Third call should cycle back to first response
        response_chunks = []
        async for chunk in provider.stream_response(messages):
            response_chunks.append(chunk)
        
        assert len(response_chunks) == 1
        assert response_chunks[0] == "Custom response 1"
    
    @pytest.mark.asyncio
    async def test_stream_response_without_custom_responses(self):
        """Test that stream_response works without custom responses."""
        provider = LocalTestModel()
        
        messages = [Message(role="user", content="Hello", agent_id="test")]
        
        response_chunks = []
        async for chunk in provider.stream_response(messages):
            response_chunks.append(chunk)
        
        assert len(response_chunks) == 1
        assert len(response_chunks[0]) > 0  # Just check that we get some response
    
    @pytest.mark.asyncio
    async def test_generate_method_still_works(self):
        """Test that the generate method still works as expected."""
        provider = LocalTestModel(responses=["Generated response"])
        
        messages = [Message(role="user", content="Test", agent_id="test")]
        
        response = await provider.generate(messages)
        assert response == "Generated response"
    
    def test_provider_interface_compliance(self):
        """Test that LocalTestModel properly implements the Provider interface."""
        from pidgin.providers.base import Provider
        
        provider = LocalTestModel()
        
        # Check that it inherits from Provider
        assert isinstance(provider, Provider)
        
        # Check that it has required methods
        assert hasattr(provider, 'stream_response')
        assert hasattr(provider, 'cleanup')
        assert hasattr(provider, 'get_last_usage')
    
    @pytest.mark.asyncio
    async def test_cleanup_method(self):
        """Test that cleanup method works."""
        provider = LocalTestModel()
        
        # Should not raise an exception
        await provider.cleanup()
    
    def test_get_last_usage_method(self):
        """Test that get_last_usage method works."""
        provider = LocalTestModel()
        
        # Should return None (default implementation)
        usage = provider.get_last_usage()
        assert usage is None