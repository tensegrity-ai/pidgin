"""Token usage event handler for DuckDB storage."""

from typing import Dict, Optional

from ..config.provider_capabilities import get_provider_capabilities
from ..core.events import MessageCompleteEvent, TokenUsageEvent
from ..io.logger import get_logger
from ..providers.token_tracker import GlobalTokenTracker
from .event_store import EventStore

logger = get_logger("token_handler")


class TokenUsageHandler:
    """Handles token usage events and stores them in DuckDB."""

    # Provider pricing in cents per 1K tokens (as of 2024)
    PRICING = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"prompt": 0.3, "completion": 1.5},
            "claude-3-5-haiku-20241022": {"prompt": 0.08, "completion": 0.4},
            "claude-3-opus-20240229": {"prompt": 1.5, "completion": 7.5},
            "claude-3-sonnet-20240229": {"prompt": 0.3, "completion": 1.5},
            "claude-3-haiku-20240307": {"prompt": 0.025, "completion": 0.125},
        },
        "openai": {
            "gpt-4-turbo-preview": {"prompt": 1.0, "completion": 3.0},
            "gpt-4-turbo": {"prompt": 1.0, "completion": 3.0},
            "gpt-4": {"prompt": 3.0, "completion": 6.0},
            "gpt-4o": {"prompt": 0.5, "completion": 1.5},
            "gpt-4o-mini": {"prompt": 0.015, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.05, "completion": 0.15},
        },
        "google": {
            "gemini-1.5-pro": {"prompt": 0.35, "completion": 1.05},
            "gemini-1.5-flash": {"prompt": 0.0075, "completion": 0.03},
            "gemini-1.0-pro": {"prompt": 0.05, "completion": 0.15},
        },
        "xai": {
            "grok-beta": {"prompt": 0.5, "completion": 1.5},
        },
    }

    def __init__(self, storage: EventStore, token_tracker: GlobalTokenTracker):
        """Initialize handler with storage backend.

        Args:
            storage: Event store for persisting token usage
            token_tracker: Token tracker for rate limiting
        """
        self.storage = storage
        self.token_tracker = token_tracker

        # Track token counts for conversations
        self.conversation_tokens: Dict[str, Dict[str, int]] = {}

    def handle_token_usage(self, event: TokenUsageEvent):
        """Handle token usage event from providers."""
        conv_id = event.conversation_id
        provider = event.provider.lower().replace("provider", "")

        # Get model from event or try to infer
        model = getattr(event, "model", None)
        if not model:
            # Try to get from stored conversation info
            model = self._get_model_from_conversation(conv_id, provider)

        # Get token breakdown from event
        prompt_tokens = getattr(event, "prompt_tokens", 0)
        completion_tokens = getattr(event, "completion_tokens", 0)
        total_tokens = event.tokens_used

        # If we don't have breakdown, estimate it
        if prompt_tokens == 0 and completion_tokens == 0 and total_tokens > 0:
            # This is a rough estimate - ideally we'd track prompt tokens separately
            prompt_tokens = int(total_tokens * 0.3)
            completion_tokens = total_tokens - prompt_tokens

        # Calculate costs with actual token breakdown
        costs = self._calculate_costs(
            provider, model, total_tokens, prompt_tokens, completion_tokens
        )

        # Store in database
        self.storage.log_token_usage(
            conversation_id=conv_id,
            provider=provider,
            model=model or "unknown",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=costs["total_cost"],
        )

        # Token tracker usage is now recorded in event_wrapper.py before emitting
        # This ensures current_usage_rate includes the current request

        logger.debug(
            f"Logged token usage for {conv_id}: {total_tokens} tokens "
            f"(prompt: {prompt_tokens}, completion: {completion_tokens}) "
            f"Cost: ${costs['total_cost'] / 100:.4f}"
        )

    def _get_rpm_limit(self, provider: str) -> int:
        """Get requests per minute limit for provider."""
        provider_key = provider.split(":")[0]  # Handle "anthropic:cached" format
        capabilities = get_provider_capabilities(provider_key)
        return capabilities.requests_per_minute

    def handle_message_complete(self, event: MessageCompleteEvent):
        """Enhanced handler that extracts provider-specific usage data."""
        conv_id = event.conversation_id

        # Track per-conversation tokens
        if conv_id not in self.conversation_tokens:
            self.conversation_tokens[conv_id] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        # Track tokens from the event
        self.conversation_tokens[conv_id]["prompt_tokens"] += event.prompt_tokens
        self.conversation_tokens[conv_id]["completion_tokens"] += (
            event.completion_tokens
        )
        self.conversation_tokens[conv_id]["total_tokens"] += event.total_tokens

    def _calculate_costs(
        self,
        provider: str,
        model: Optional[str],
        tokens: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Dict[str, float]:
        """Calculate costs based on provider pricing."""
        # Default to total tokens if breakdown not available
        if prompt_tokens == 0 and completion_tokens == 0:
            # Rough estimate: 30% prompt, 70% completion
            prompt_tokens = int(tokens * 0.3)
            completion_tokens = tokens - prompt_tokens

        # Get pricing for model
        provider_pricing = self.PRICING.get(provider, {})
        model_pricing = None

        if model:
            # Try exact match first
            model_pricing = provider_pricing.get(model)

            # If not found, try to match by prefix
            if not model_pricing:
                for model_key, pricing in provider_pricing.items():
                    if model.startswith(model_key) or model_key in model:
                        model_pricing = pricing
                        break

        # Default pricing if model not found
        if not model_pricing:
            model_pricing = {"prompt": 0.05, "completion": 0.15}  # Conservative default
            logger.warning(f"No pricing found for {provider}/{model}, using defaults")

        # Calculate costs in cents
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
        total_cost = prompt_cost + completion_cost

        return {
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": total_cost,
        }

    def _get_model_from_conversation(
        self, conv_id: str, provider: str
    ) -> Optional[str]:
        """Get model name from conversation data."""
        # This would query the conversations table
        # For now, return None
        return None

    def get_conversation_costs(self, conv_id: str) -> Dict[str, float]:
        """Get total costs for a conversation."""
        tokens = self.conversation_tokens.get(conv_id, {})
        if not tokens:
            return {"prompt_cost": 0.0, "completion_cost": 0.0, "total_cost": 0.0}

        # This is a simplified version - in reality we'd sum from the database
        return {"prompt_cost": 0.0, "completion_cost": 0.0, "total_cost": 0.0}
