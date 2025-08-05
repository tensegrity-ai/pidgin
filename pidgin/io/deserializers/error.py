"""Deserializers for error events."""

from datetime import datetime
from typing import Any, Dict

from ...core.events import (
    APIErrorEvent,
    ErrorEvent,
    ProviderTimeoutEvent,
)
from .base import BaseDeserializer


class ErrorDeserializer(BaseDeserializer):
    """Deserialize error events."""

    @classmethod
    def build_error(cls, data: Dict[str, Any], timestamp: datetime) -> ErrorEvent:
        """Build ErrorEvent from data."""
        return ErrorEvent(
            timestamp=timestamp,
            conversation_id=data.get("conversation_id"),
            experiment_id=data.get("experiment_id"),
            error_type=data.get("error_type", "unknown"),
            error_message=data.get("error_message", ""),
            context=data.get("context"),
        )

    @classmethod
    def build_api_error(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> APIErrorEvent:
        """Build APIErrorEvent from data."""
        return APIErrorEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            provider=data["provider"],
            error_message=data["error_message"],
            error_code=data.get("error_code"),
            retryable=data.get("retryable", False),
        )

    @classmethod
    def build_provider_timeout(
        cls, data: Dict[str, Any], timestamp: datetime
    ) -> ProviderTimeoutEvent:
        """Build ProviderTimeoutEvent from data."""
        return ProviderTimeoutEvent(
            timestamp=timestamp,
            conversation_id=data["conversation_id"],
            experiment_id=data.get("experiment_id"),
            agent_id=data["agent_id"],
            provider=data["provider"],
            timeout_seconds=data["timeout_seconds"],
            error_message=data.get("error_message", "Provider timeout"),
            context=data.get("context"),
        )