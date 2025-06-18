"""Context window management for AI providers."""

import os
import math
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from ..core.types import Message
from ..config import get_config
from ..io.logger import get_logger

logger = get_logger("context_manager")


class ProviderContextManager:
    """Manages context windows and message truncation for different providers.
    
    Each provider has different context window limits and pricing models.
    This manager ensures we stay within limits while preserving conversation quality.
    """
    
    # Default context limits (in tokens) - conservative estimates
    DEFAULT_CONTEXT_LIMITS = {
        "anthropic": 180000,    # 90% of 200k limit
        "openai": 120000,       # ~94% of 128k limit  
        "google": 900000,       # 90% of 1M+ limit
        "xai": 120000,          # ~94% of 128k limit
    }
    
    # Model-specific context limits (when known)
    MODEL_CONTEXT_LIMITS = {
        # Anthropic models
        "claude-3-opus-20240229": 200000,
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-5-haiku-20241022": 200000,
        
        # OpenAI models  
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "o1-preview": 128000,
        "o1-mini": 128000,
        
        # Google models
        "gemini-1.5-pro": 2097152,    # 2M tokens!
        "gemini-1.5-flash": 1048576,  # 1M tokens
        "gemini-2.0-flash-exp": 1048576,
        
        # xAI models
        "grok-beta": 131072,
        "grok-2-beta": 131072,
    }
    
    # Token estimation constants
    CHARS_PER_TOKEN = 4  # Conservative estimate: 1 token ≈ 4 characters
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize context manager with configuration.
        
        Args:
            config: Provider configuration dict
        """
        self.config = config or get_config().get("providers.context_management", {})
        self._load_limits()
        
    def _load_limits(self):
        """Load context limits from config with defaults."""
        self.context_limits = self.DEFAULT_CONTEXT_LIMITS.copy()
        
        # Override with config if provided
        overrides = get_config().get("providers.overrides", {})
        for provider, settings in overrides.items():
            if "context_limit" in settings:
                self.context_limits[provider] = settings["context_limit"]
    
    def prepare_context(
        self,
        messages: List[Message],
        provider: str,
        model: Optional[str] = None
    ) -> List[Message]:
        """Prepare messages for API call with smart truncation if needed.
        
        Args:
            messages: Full conversation history
            provider: Provider name (anthropic, openai, etc)
            model: Optional specific model name for per-model limits
            
        Returns:
            List of messages safe to send to the API
        """
        # Check for environment variable override first
        if max_tokens := os.getenv("PIDGIN_MAX_CONTEXT_TOKENS"):
            return self._truncate_to_limit(messages, int(max_tokens))
            
        if not self.config.get("enabled", True):
            return messages
            
        # Get provider key
        provider_key = provider.lower().replace("provider", "")
        
        # Use provider-specific strategy
        if provider_key == "anthropic":
            return self._truncate_claude(messages, model)
        elif provider_key == "openai":
            return self._truncate_gpt(messages, model)
        elif provider_key == "google":
            return self._truncate_gemini(messages, model)
        elif provider_key == "xai":
            return self._truncate_grok(messages, model)
        else:
            return self._truncate_default(messages, provider_key, model)
    
    def _estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Estimated token count
        """
        # Simple character-based estimation
        # More sophisticated estimation could use tiktoken or provider-specific tokenizers
        total_chars = sum(len(m.content) for m in messages)
        
        # Add overhead for message structure (role, etc)
        overhead_per_message = 4  # tokens for role + formatting
        total_overhead = len(messages) * overhead_per_message
        
        return math.ceil(total_chars / self.CHARS_PER_TOKEN) + total_overhead
    
    def _truncate_sliding_window(
        self,
        messages: List[Message],
        token_limit: int,
        min_messages: int
    ) -> List[Message]:
        """Truncate using sliding window strategy.
        
        Keeps system messages and recent conversation.
        
        Args:
            messages: Full message list
            token_limit: Maximum tokens allowed
            min_messages: Minimum messages to keep
            
        Returns:
            Truncated message list
        """
        if len(messages) <= min_messages:
            return messages
            
        # Separate system and conversation messages
        system_messages = [m for m in messages if m.role == "system"]
        other_messages = [m for m in messages if m.role != "system"]
        
        # Always keep system messages
        system_tokens = self._estimate_tokens(system_messages)
        remaining_tokens = token_limit - system_tokens
        
        if remaining_tokens <= 0:
            # System messages alone exceed limit - unusual but handle it
            logger.warning("System messages alone exceed token limit")
            return system_messages[-1:]  # Keep only last system message
        
        # Binary search for how many recent messages we can keep
        left, right = min_messages, len(other_messages)
        best_count = min_messages
        
        while left <= right:
            mid = (left + right) // 2
            recent_messages = other_messages[-mid:]
            tokens = self._estimate_tokens(recent_messages)
            
            if tokens <= remaining_tokens:
                best_count = mid
                left = mid + 1
            else:
                right = mid - 1
        
        # Take the best number of recent messages
        kept_messages = other_messages[-best_count:]
        
        logger.debug(
            f"Truncated from {len(messages)} to {len(system_messages) + len(kept_messages)} messages"
        )
        
        return system_messages + kept_messages
    
    def get_context_usage(
        self,
        messages: List[Message],
        provider: str
    ) -> Tuple[int, int, float]:
        """Get context usage statistics.
        
        Args:
            messages: Current messages
            provider: Provider name
            
        Returns:
            Tuple of (used_tokens, limit_tokens, usage_percentage)
        """
        provider_key = provider.lower().replace("provider", "")
        limit = self.context_limits.get(provider_key, 100000)
        used = self._estimate_tokens(messages)
        percentage = (used / limit) * 100 if limit > 0 else 0
        
        return used, limit, percentage
    
    def _truncate_claude(self, messages: List[Message], model: Optional[str]) -> List[Message]:
        """Truncation strategy for Anthropic Claude models.
        
        Claude has large context windows (200k) and handles long contexts well.
        Strategy: Conservative truncation, preserve conversation flow.
        """
        # Get model-specific or provider default limit
        if model and model in self.MODEL_CONTEXT_LIMITS:
            base_limit = self.MODEL_CONTEXT_LIMITS[model]
        else:
            base_limit = self.context_limits.get("anthropic", 180000)
        
        # Claude strategy: more conservative, keep more context
        safety_factor = 0.9  # Use 90% of limit
        reserve_ratio = 0.2  # Reserve 20% for response
        min_messages = max(20, self.config.get("min_messages_retained", 10))
        
        available_tokens = int(base_limit * safety_factor * (1 - reserve_ratio))
        
        total_tokens = self._estimate_tokens(messages)
        if total_tokens <= available_tokens:
            return messages
            
        logger.info(
            f"Claude truncation: {total_tokens} tokens > {available_tokens} available"
        )
        
        return self._truncate_sliding_window(messages, available_tokens, min_messages)
    
    def _truncate_gpt(self, messages: List[Message], model: Optional[str]) -> List[Message]:
        """Truncation strategy for OpenAI GPT models.
        
        GPT has smaller context windows (128k) but handles context switches well.
        Strategy: More aggressive truncation, focus on recent messages.
        """
        # Get model-specific or provider default limit
        if model and model in self.MODEL_CONTEXT_LIMITS:
            base_limit = self.MODEL_CONTEXT_LIMITS[model]
        else:
            base_limit = self.context_limits.get("openai", 120000)
        
        # GPT strategy: more aggressive truncation
        safety_factor = 0.85  # Use 85% of limit
        reserve_ratio = 0.3   # Reserve 30% for response
        min_messages = self.config.get("min_messages_retained", 10)
        
        available_tokens = int(base_limit * safety_factor * (1 - reserve_ratio))
        
        total_tokens = self._estimate_tokens(messages)
        if total_tokens <= available_tokens:
            return messages
            
        logger.info(
            f"GPT truncation: {total_tokens} tokens > {available_tokens} available"
        )
        
        return self._truncate_sliding_window(messages, available_tokens, min_messages)
    
    def _truncate_gemini(self, messages: List[Message], model: Optional[str]) -> List[Message]:
        """Truncation strategy for Google Gemini models.
        
        Gemini has huge context windows (1M-2M) but can be slow with very large contexts.
        Strategy: Balanced approach, use context wisely.
        """
        # Get model-specific or provider default limit
        if model and model in self.MODEL_CONTEXT_LIMITS:
            base_limit = self.MODEL_CONTEXT_LIMITS[model]
        else:
            base_limit = self.context_limits.get("google", 900000)
        
        # Gemini strategy: balanced, but cap at reasonable size for performance
        # Even though Gemini supports 1M+ tokens, very large contexts can be slow
        performance_cap = 200000  # Cap at 200k for performance
        base_limit = min(base_limit, performance_cap)
        
        safety_factor = 0.9   # Use 90% of limit
        reserve_ratio = 0.25  # Reserve 25% for response
        min_messages = max(15, self.config.get("min_messages_retained", 10))
        
        available_tokens = int(base_limit * safety_factor * (1 - reserve_ratio))
        
        total_tokens = self._estimate_tokens(messages)
        if total_tokens <= available_tokens:
            return messages
            
        logger.info(
            f"Gemini truncation: {total_tokens} tokens > {available_tokens} available"
        )
        
        return self._truncate_sliding_window(messages, available_tokens, min_messages)
    
    def _truncate_grok(self, messages: List[Message], model: Optional[str]) -> List[Message]:
        """Truncation strategy for xAI Grok models.
        
        Grok has moderate context windows (128k) similar to GPT.
        Strategy: Similar to GPT, focus on recent context.
        """
        # Get model-specific or provider default limit
        if model and model in self.MODEL_CONTEXT_LIMITS:
            base_limit = self.MODEL_CONTEXT_LIMITS[model]
        else:
            base_limit = self.context_limits.get("xai", 120000)
        
        # Grok strategy: similar to GPT
        safety_factor = 0.85  # Use 85% of limit
        reserve_ratio = 0.3   # Reserve 30% for response
        min_messages = self.config.get("min_messages_retained", 10)
        
        available_tokens = int(base_limit * safety_factor * (1 - reserve_ratio))
        
        total_tokens = self._estimate_tokens(messages)
        if total_tokens <= available_tokens:
            return messages
            
        logger.info(
            f"Grok truncation: {total_tokens} tokens > {available_tokens} available"
        )
        
        return self._truncate_sliding_window(messages, available_tokens, min_messages)
    
    def _truncate_default(
        self, 
        messages: List[Message], 
        provider: str, 
        model: Optional[str]
    ) -> List[Message]:
        """Default truncation strategy for unknown providers."""
        # Use conservative defaults
        base_limit = self.context_limits.get(provider, 100000)
        
        safety_factor = self.config.get("safety_factor", 0.9)
        reserve_ratio = self.config.get("context_reserve_ratio", 0.25)
        min_messages = self.config.get("min_messages_retained", 10)
        
        available_tokens = int(base_limit * safety_factor * (1 - reserve_ratio))
        
        total_tokens = self._estimate_tokens(messages)
        if total_tokens <= available_tokens:
            return messages
            
        logger.info(
            f"Default truncation for {provider}: "
            f"{total_tokens} tokens > {available_tokens} available"
        )
        
        return self._truncate_sliding_window(messages, available_tokens, min_messages)
    
    def _truncate_to_limit(self, messages: List[Message], token_limit: int) -> List[Message]:
        """Truncate to a specific token limit (from env var)."""
        min_messages = int(os.getenv("PIDGIN_MIN_MESSAGES", "10"))
        
        total_tokens = self._estimate_tokens(messages)
        if total_tokens <= token_limit:
            return messages
            
        logger.info(
            f"Env var truncation: {total_tokens} tokens > {token_limit} limit"
        )
        
        return self._truncate_sliding_window(messages, token_limit, min_messages)