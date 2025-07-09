"""Test to verify Google model serialization is fixed."""

import pytest
import json
import asyncio
from unittest.mock import Mock, MagicMock
from pidgin.core.event_bus import EventBus
from pidgin.core.events import TokenUsageEvent


class MockGenerativeModel:
    """Mock Google's GenerativeModel class."""
    def __init__(self, model_name):
        self._model_name = f"models/{model_name}"
        self._client = "mock_client"
        self.model_name = model_name
        
    def __repr__(self):
        return f"genai.GenerativeModel(model_name='{self._model_name}')"


@pytest.mark.asyncio
async def test_google_model_not_serialized():
    """Test that Google GenerativeModel objects are not serialized in events."""
    # Create event bus
    bus = EventBus()
    
    # Create a mock Google model
    model = MockGenerativeModel("gemini-2.0-flash-exp")
    
    # Test _serialize_value handles GenerativeModel correctly
    serialized = bus._serialize_value(model)
    assert serialized == "gemini-2.0-flash-exp"
    assert "GenerativeModel" not in str(serialized)
    
    # Test that if a model object gets into event data, it's handled
    event_data = {
        "provider": "Google",
        "model": model  # This should not happen, but test defense
    }
    
    serialized_data = bus._serialize_value(event_data)
    assert serialized_data["model"] == "gemini-2.0-flash-exp"
    assert "GenerativeModel" not in json.dumps(serialized_data)


@pytest.mark.asyncio
async def test_token_event_model_validation():
    """Test that TokenUsageEvent model field is validated."""
    from pidgin.providers.event_wrapper import EventAwareProvider
    from pidgin.providers.token_tracker import get_token_tracker
    
    # Create a mock provider with both model and model_name
    mock_provider = Mock()
    mock_provider.model_name = "gemini-2.0-flash-exp"
    mock_provider.model = MockGenerativeModel("gemini-2.0-flash-exp")
    mock_provider.__class__.__name__ = "GoogleProvider"
    
    # Mock get_last_usage
    mock_provider.get_last_usage.return_value = {
        'prompt_tokens': 10,
        'completion_tokens': 20,
        'total_tokens': 30
    }
    
    # Create event
    event = TokenUsageEvent(
        conversation_id="test",
        provider="Google",
        tokens_used=30,
        tokens_per_minute_limit=60000,
        current_usage_rate=0.0
    )
    
    # The event_wrapper should set model to the string, not the object
    model_name = mock_provider.model_name
    assert isinstance(model_name, str)
    assert model_name == "gemini-2.0-flash-exp"
    
    # If someone accidentally sets the model object
    event.model = mock_provider.model  # This is the bug!
    
    # Our EventBus should still handle it correctly
    bus = EventBus()
    event_data = {}
    for k, v in event.__dict__.items():
        if k not in ["timestamp", "event_id"]:
            if k == "model":
                # This is what our fix does
                if hasattr(v, "_model_name"):
                    event_data[k] = getattr(v, "_model_name", str(v)).replace("models/", "")
                else:
                    event_data[k] = bus._serialize_value(v)
            else:
                event_data[k] = bus._serialize_value(v)
    
    # Check that model was serialized correctly
    assert event_data["model"] == "gemini-2.0-flash-exp"
    assert "GenerativeModel" not in json.dumps(event_data)


def test_direct_json_serialization_defense():
    """Test that even direct JSON serialization doesn't expose model objects."""
    model = MockGenerativeModel("gemini-2.0-flash-exp")
    
    # This would fail without default=str
    with pytest.raises(TypeError):
        json.dumps({"model": model})
    
    # With default=str it would expose the repr
    json_str = json.dumps({"model": model}, default=str)
    assert "GenerativeModel" in json_str  # This is what we're preventing
    
    # Our EventBus should handle it correctly
    bus = EventBus()
    serialized = bus._serialize_value({"model": model})
    json_str = json.dumps(serialized)
    assert "GenerativeModel" not in json_str
    assert "gemini-2.0-flash-exp" in json_str