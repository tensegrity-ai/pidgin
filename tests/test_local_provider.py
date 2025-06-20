"""Tests for LocalProvider functionality."""
import pytest
import asyncio
from pidgin.providers.local import LocalProvider
from pidgin.core.types import Message


@pytest.mark.asyncio
async def test_local_provider_works():
    """Test that local provider works offline."""
    provider = LocalProvider("test")
    
    messages = [
        Message(role="user", content="Hello, how are you?", agent_id="user")
    ]
    
    response = ""
    async for chunk in provider.stream_response(messages):
        response += chunk
        
    assert len(response) > 0
    # Test model responds to greetings with a question response
    assert "question" in response.lower() or "thoughts" in response.lower()


@pytest.mark.asyncio
async def test_local_provider_streaming():
    """Test that responses are properly streamed."""
    provider = LocalProvider("test")
    
    messages = [
        Message(role="user", content="Tell me about patterns", agent_id="user")
    ]
    
    chunks = []
    async for chunk in provider.stream_response(messages):
        chunks.append(chunk)
        
    # Should receive multiple chunks (words)
    assert len(chunks) > 5
    
    # Reconstruct message
    full_response = "".join(chunks)
    # Should contain contextual response about the topic
    assert len(full_response) > 20  # Non-trivial response


@pytest.mark.asyncio
async def test_local_provider_convergence():
    """Test convergence behavior after many turns."""
    provider = LocalProvider("test")
    
    messages = []
    
    # Simulate a long conversation
    for i in range(15):
        if i == 0:
            messages.append(Message(role="user", content="Let's have a conversation", agent_id="user"))
        else:
            messages.append(Message(role="user", content="I agree, please continue", agent_id="user"))
            
        # Get assistant response
        response = ""
        async for chunk in provider.stream_response(messages):
            response += chunk
            
        messages.append(Message(role="assistant", content=response, agent_id="assistant"))
    
    # Last response should be short (convergence)
    last_response = messages[-1].content
    assert len(last_response.split()) < 5  # Very short response


@pytest.mark.asyncio
async def test_local_provider_deterministic():
    """Test that responses are deterministic."""
    provider = LocalProvider("test")
    
    messages = [
        Message(role="user", content="What is the meaning of life?", agent_id="user")
    ]
    
    # Get response twice
    response1 = ""
    async for chunk in provider.stream_response(messages):
        response1 += chunk
        
    response2 = ""
    async for chunk in provider.stream_response(messages):
        response2 += chunk
        
    # Should be identical
    assert response1 == response2


@pytest.mark.asyncio
async def test_local_provider_unsupported_model():
    """Test error handling for unsupported models."""
    provider = LocalProvider("qwen-0.5b")
    
    messages = [
        Message(role="user", content="Hello", agent_id="user")
    ]
    
    with pytest.raises(ValueError) as exc_info:
        async for chunk in provider.stream_response(messages):
            pass
            
    assert "not yet supported" in str(exc_info.value)
    assert "test" in str(exc_info.value)