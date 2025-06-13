"""Context window management for preventing conversation size limit crashes."""

import logging
from typing import List, Dict, Any, Union
from .types import Message

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """Track conversation size relative to model context limits"""
    
    def __init__(self):
        # Context window sizes (in tokens)
        self.context_limits = {
            # Anthropic Claude models (200k context)
            'claude-4-opus-20250514': 200000,
            'claude-4-sonnet-20250514': 200000,
            'claude-3-5-haiku-20241022': 200000,
            'claude-3-5-sonnet-20241022': 200000,
            'claude-3-opus-20240229': 200000,
            
            # OpenAI GPT-4 models (128k context)
            'gpt-4-turbo-2024-04-09': 128000,
            'gpt-4-turbo': 128000,
            'gpt-4-0125-preview': 128000,
            'gpt-4-1106-preview': 128000,
            'gpt-4o': 128000,
            'gpt-4o-mini': 128000,
            
            # OpenAI GPT-4.1 models
            'gpt-4.1': 128000,
            'gpt-4.1-mini': 128000,
            'gpt-4.1-nano': 128000,
            
            # OpenAI O-series models (varying limits)
            'o1-preview': 128000,
            'o1-mini': 128000,
            'o3-mini': 100000,
            'o4-mini': 100000,
            
            # Legacy models with smaller contexts
            'gpt-3.5-turbo': 16385,
            'gpt-3.5-turbo-16k': 16385,
        }
        
        # Reserve some tokens for system prompts and response
        self.reserved_tokens = 2000
        
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens using appropriate tokenizer"""
        try:
            if any(prefix in model.lower() for prefix in ['gpt', 'o1', 'o3', 'o4']):
                # For OpenAI models, we'd use tiktoken if available
                # For now, use approximation: ~1 token per 4 chars
                return len(text) // 4
            else:
                # Claude models - similar approximation
                return len(text) // 4
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}, using approximation")
            return len(text) // 4
    
    def get_conversation_size(self, messages: Union[List[Message], List[Dict[str, Any]]], model: str) -> int:
        """Calculate total tokens in conversation history"""
        total = 0
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get('content', '')
            else:
                # Handle Message objects
                content = getattr(msg, 'content', '')
            total += self.count_tokens(str(content), model)
            # Add overhead for message structure
            total += 10  # Approximate tokens for role, etc.
        return total
        
    def get_remaining_capacity(self, messages: Union[List[Message], List[Dict[str, Any]]], model: str) -> Dict[str, Any]:
        """Calculate how much context window remains"""
        limit = self.context_limits.get(model, 100000)  # Conservative default
        effective_limit = limit - self.reserved_tokens
        used = self.get_conversation_size(messages, model)
        
        return {
            'used': used,
            'limit': effective_limit,
            'total_limit': limit,
            'remaining': max(0, effective_limit - used),
            'percentage': min(100, (used / effective_limit) * 100) if effective_limit > 0 else 100
        }
        
    def predict_turns_remaining(self, messages: Union[List[Message], List[Dict[str, Any]]], model: str) -> int:
        """Estimate how many more turns before hitting limit"""
        if len(messages) < 4:  # Need history to predict
            return 999
            
        # Calculate average tokens per exchange (last 5 exchanges)
        recent_sizes = []
        for i in range(max(0, len(messages)-10), len(messages), 2):
            if i+1 < len(messages):
                # Handle first message
                msg1 = messages[i]
                if isinstance(msg1, dict):
                    content1 = msg1.get('content', '')
                else:
                    content1 = getattr(msg1, 'content', '')
                
                # Handle second message
                msg2 = messages[i+1]
                if isinstance(msg2, dict):
                    content2 = msg2.get('content', '')
                else:
                    content2 = getattr(msg2, 'content', '')
                    
                exchange_size = (self.count_tokens(str(content1), model) + 
                               self.count_tokens(str(content2), model))
                recent_sizes.append(exchange_size)
        
        if not recent_sizes:
            return 999
            
        # Calculate growth trend
        avg_exchange_size = sum(recent_sizes) / len(recent_sizes)
        
        # If messages are getting longer, adjust prediction
        if len(recent_sizes) >= 2:
            recent_growth = recent_sizes[-1] - recent_sizes[-2]
            if recent_growth > 0:
                # Messages are expanding - be more conservative
                avg_exchange_size *= 1.2
        
        capacity = self.get_remaining_capacity(messages, model)
        remaining_tokens = capacity['remaining']
        
        # Account for cumulative growth (each turn includes all history)
        current_size = capacity['used']
        turns = 0
        
        while remaining_tokens > 0 and turns < 1000:
            # Next exchange will add avg_exchange_size to history
            # But the API call will send current_size + avg_exchange_size tokens
            next_call_size = current_size + avg_exchange_size
            if next_call_size > capacity['limit']:
                break
            current_size = next_call_size
            remaining_tokens = capacity['limit'] - current_size
            turns += 1
            
        return max(1, turns)
    
    def should_warn(self, messages: Union[List[Message], List[Dict[str, Any]]], model: str, 
                    warning_threshold: int = 80) -> bool:
        """Check if we should warn about context usage"""
        capacity = self.get_remaining_capacity(messages, model)
        return bool(capacity['percentage'] >= warning_threshold)
    
    def should_pause(self, messages: Union[List[Message], List[Dict[str, Any]]], model: str,
                    pause_threshold: int = 95) -> bool:
        """Check if we should auto-pause due to context limits"""
        capacity = self.get_remaining_capacity(messages, model)
        return bool(capacity['percentage'] >= pause_threshold)
    
    def format_usage(self, capacity: Dict[str, Any]) -> str:
        """Format context usage for display"""
        return (f"{capacity['used']:,}/{capacity['limit']:,} tokens "
                f"({capacity['percentage']:.1f}%)")
    
    def get_truncation_point(self, messages: Union[List[Message], List[Dict[str, Any]]], model: str,
                           target_percentage: float = 50) -> int:
        """Find where to truncate messages to reach target capacity"""
        target_size = int(self.context_limits.get(model, 100000) * target_percentage / 100)
        
        # Keep recent messages and work backwards
        total = 0
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, dict):
                content = msg.get('content', '')
            else:
                content = getattr(msg, 'content', '')
            total += self.count_tokens(str(content), model) + 10
            
            if total > target_size:
                # Return index of first message to keep
                return max(0, i + 1)
        
        return 0  # Keep all messages