# pidgin/providers/context_manager.py
"""Minimal context window management - just prevent errors, nothing fancy."""

from typing import List, Optional
import logging

from ..core.types import Message
from ..core.events import ContextTruncationEvent

logger = logging.getLogger(__name__)


class ProviderContextManager:
    """Dead simple context truncation - just keep conversations under limits."""
    
    # Conservative limits to avoid errors (80% of actual limits)
    CONTEXT_LIMITS = {
        "anthropic": 160000,    # 200k actual
        "openai": 100000,       # 128k actual  
        "google": 800000,       # 1M+ actual
        "xai": 100000,          # 128k actual
        "local": 4000,          # Most local models are 4k-8k
    }
    
    # Model-specific limits (when known)
    MODEL_LIMITS = {
        # Local models via Ollama
        "qwen2.5:3b": 32768,    # 32k context
        "phi3": 4096,           # 4k context
        "mistral": 8192,        # 8k context
        "llama3.2": 131072,     # 128k context
        # Add more as needed
    }
    
    # Token estimation: 1 token ≈ 3.5 chars (conservative for cost estimates)
    # Real ratios: English ~4.2, Code ~2.8, Dense text ~5.0
    CHARS_PER_TOKEN = 3.5
    
    def prepare_context(
        self, 
        messages: List[Message], 
        provider: str, 
        model: Optional[str] = None,
        event_bus=None,
        conversation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> List[Message]:
        """Keep messages under context limit - that's it."""
        
        # Check model-specific limit first, then provider limit
        limit = self.MODEL_LIMITS.get(model, self.CONTEXT_LIMITS.get(provider, 8000))
        
        # Quick estimate of total size
        total_chars = sum(len(m.content) + 20 for m in messages)  # +20 for role/formatting
        estimated_tokens = int(total_chars / self.CHARS_PER_TOKEN)
        
        # If under limit, return as-is
        if estimated_tokens < limit:
            return messages
        
        # Over limit - keep system messages + recent conversation
        system_messages = [m for m in messages if m.role == "system"]
        other_messages = [m for m in messages if m.role != "system"]
        
        # Binary search for how many recent messages fit
        left, right = 1, len(other_messages)
        best = 1
        
        while left <= right:
            mid = (left + right) // 2
            test_messages = system_messages + other_messages[-mid:]
            test_chars = sum(len(m.content) + 20 for m in test_messages)
            test_tokens = int(test_chars / self.CHARS_PER_TOKEN)
            
            if test_tokens < limit:
                best = mid
                left = mid + 1
            else:
                right = mid - 1
        
        result = system_messages + other_messages[-best:]
        final_tokens = int(sum(len(m.content) + 20 for m in result) / self.CHARS_PER_TOKEN)
        
        if len(result) < len(messages):
            # Log at INFO level with a minimal message for visibility
            logger.info(f"✂ Context truncated: {len(messages)} → {len(result)} messages")
            logger.debug(
                f"Truncated {provider} context: {len(messages)} → {len(result)} messages "
                f"(~{estimated_tokens:,} → {final_tokens:,} tokens, limit: {limit:,})"
            )
            
            # Emit truncation event if event bus is available
            if event_bus and conversation_id and agent_id is not None and turn_number is not None:
                try:
                    import asyncio
                    event = ContextTruncationEvent(
                        conversation_id=conversation_id,
                        agent_id=agent_id,
                        provider=provider,
                        model=model or "unknown",
                        turn_number=turn_number,
                        original_message_count=len(messages),
                        truncated_message_count=len(result),
                        messages_dropped=len(messages) - len(result)
                    )
                    # Emit the event - EventBus.emit is always async
                    # Since we're already in an async context (providers are async),
                    # we can create a task to emit without blocking
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(event_bus.emit(event))
                    except RuntimeError:
                        # No running loop, skip emission
                        logger.debug("No running event loop, skipping truncation event emission")
                except Exception as e:
                    logger.warning(f"Failed to emit truncation event: {e}")
        
        return result