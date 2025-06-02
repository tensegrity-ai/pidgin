"""Token management for preventing rate limit crashes in AI conversations."""

import time
from typing import Dict, List, Tuple, Optional
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TokenManager:
    """Track token usage across providers and predict rate limits."""
    
    def __init__(self):
        # Rate limits per model (rpm = requests per minute, tpm = tokens per minute)
        self.limits = {
            # Anthropic Claude models
            'claude-4-opus-20250514': {'rpm': 50, 'tpm': 40000},
            'claude-4-sonnet-20250514': {'rpm': 50, 'tpm': 40000},
            'claude-3-5-haiku-20241022': {'rpm': 50, 'tpm': 40000},
            'claude-3-5-sonnet-20241022': {'rpm': 50, 'tpm': 40000},
            'claude-3-opus-20240229': {'rpm': 50, 'tpm': 40000},
            
            # OpenAI GPT models
            'gpt-4-turbo-2024-04-09': {'rpm': 500, 'tpm': 80000},
            'gpt-4-0125-preview': {'rpm': 500, 'tpm': 80000},
            'gpt-4-1106-preview': {'rpm': 500, 'tpm': 80000},
            'gpt-4.1': {'rpm': 500, 'tpm': 80000},
            'gpt-4.1-mini': {'rpm': 500, 'tpm': 80000},
            'gpt-4.1-nano': {'rpm': 1000, 'tpm': 200000},
            
            # OpenAI O-series models
            'o3-mini': {'rpm': 100, 'tpm': 50000},
            'o4-mini': {'rpm': 100, 'tpm': 50000},
        }
        
        # Track usage per model with sliding window (1 minute)
        self.usage_windows: Dict[str, deque] = {}
        self.request_windows: Dict[str, deque] = {}
        
    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens for text using model-specific tokenizer.
        Uses approximation for now - can be made more accurate with tiktoken.
        """
        # Simple approximation: ~4 chars per token for Claude, ~3.5 for GPT
        if model.startswith('claude'):
            return len(text) // 4
        else:  # GPT and O-series
            return int(len(text) / 3.5)
    
    def _clean_window(self, window: deque, cutoff_time: datetime):
        """Remove entries older than cutoff time."""
        while window and window[0][0] < cutoff_time:
            window.popleft()
    
    def check_availability(self, model: str, new_tokens: int) -> Tuple[bool, int]:
        """
        Check if we have budget for new_tokens.
        Returns: (can_proceed, seconds_until_available)
        """
        if model not in self.limits:
            # Unknown model - assume generous limits
            return True, 0
        
        limits = self.limits[model]
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Initialize windows if needed
        if model not in self.usage_windows:
            self.usage_windows[model] = deque()
            self.request_windows[model] = deque()
        
        # Clean old entries
        self._clean_window(self.usage_windows[model], cutoff)
        self._clean_window(self.request_windows[model], cutoff)
        
        # Calculate current usage
        current_tokens = sum(tokens for _, tokens in self.usage_windows[model])
        current_requests = len(self.request_windows[model])
        
        # Check if adding new tokens would exceed limits
        if current_tokens + new_tokens > limits['tpm']:
            # Find when oldest tokens expire
            if self.usage_windows[model]:
                oldest_time = self.usage_windows[model][0][0]
                seconds_until_available = int((oldest_time + timedelta(minutes=1) - now).total_seconds())
                return False, max(1, seconds_until_available)
            return False, 60
        
        # Check request limit
        if current_requests + 1 > limits['rpm']:
            if self.request_windows[model]:
                oldest_time = self.request_windows[model][0][0]
                seconds_until_available = int((oldest_time + timedelta(minutes=1) - now).total_seconds())
                return False, max(1, seconds_until_available)
            return False, 60
        
        return True, 0
    
    def track_usage(self, model: str, tokens: int):
        """Record token consumption."""
        if model not in self.usage_windows:
            self.usage_windows[model] = deque()
            self.request_windows[model] = deque()
        
        now = datetime.now()
        self.usage_windows[model].append((now, tokens))
        self.request_windows[model].append((now, 1))
        
        logger.debug(f"Tracked {tokens} tokens for {model}")
    
    def get_usage_stats(self, model: str) -> Dict[str, any]:
        """Get current usage statistics for a model."""
        if model not in self.limits:
            return {'tokens_used': 0, 'tokens_limit': 0, 'percentage': 0}
        
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        if model in self.usage_windows:
            self._clean_window(self.usage_windows[model], cutoff)
            tokens_used = sum(tokens for _, tokens in self.usage_windows[model])
        else:
            tokens_used = 0
        
        tokens_limit = self.limits[model]['tpm']
        percentage = (tokens_used / tokens_limit * 100) if tokens_limit > 0 else 0
        
        return {
            'tokens_used': tokens_used,
            'tokens_limit': tokens_limit,
            'percentage': percentage
        }


class ConversationTokenPredictor:
    """Predict when conversation will hit rate limits."""
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.history: List[Tuple[int, int]] = []  # (prompt_tokens, response_tokens)
        
    def add_exchange(self, prompt_tokens: int, response_tokens: int):
        """Track tokens for this exchange."""
        self.history.append((prompt_tokens, response_tokens))
        
    def predict_remaining_exchanges(self, model_a: str, model_b: str) -> int:
        """Estimate exchanges until rate limit based on growth pattern."""
        if len(self.history) < 2:
            # Not enough data - assume we have plenty of room
            return 100
        
        # Calculate average growth rate
        total_tokens = []
        for i, (prompt, response) in enumerate(self.history):
            # Each exchange adds to the conversation history
            cumulative = sum(p + r for p, r in self.history[:i+1])
            total_tokens.append(cumulative)
        
        # Estimate growth rate (tokens per exchange)
        if len(total_tokens) >= 2:
            recent_growth = total_tokens[-1] - total_tokens[-2]
            avg_growth = sum(total_tokens[i] - total_tokens[i-1] 
                           for i in range(1, len(total_tokens))) / (len(total_tokens) - 1)
            
            # Use weighted average favoring recent growth
            growth_rate = (recent_growth * 0.7 + avg_growth * 0.3)
        else:
            growth_rate = total_tokens[-1]
        
        # Get current usage for both models
        stats_a = self.token_manager.get_usage_stats(model_a)
        stats_b = self.token_manager.get_usage_stats(model_b)
        
        # Find the most constrained model
        remaining_a = stats_a['tokens_limit'] - stats_a['tokens_used']
        remaining_b = stats_b['tokens_limit'] - stats_b['tokens_used']
        remaining_tokens = min(remaining_a, remaining_b)
        
        # Predict exchanges until limit
        if growth_rate <= 0:
            return 100  # No growth or shrinking - we're fine
        
        exchanges_remaining = int(remaining_tokens / (growth_rate * 2))  # *2 for both agents
        
        # Account for compression attractors (messages getting shorter)
        if len(self.history) >= 5:
            # Check if recent messages are shrinking
            recent_sizes = [p + r for p, r in self.history[-5:]]
            if all(recent_sizes[i] <= recent_sizes[i-1] for i in range(1, len(recent_sizes))):
                # Compression detected - we might have more exchanges
                exchanges_remaining = int(exchanges_remaining * 1.5)
        
        return max(1, exchanges_remaining)
    
    def get_growth_pattern(self) -> str:
        """Describe the token growth pattern."""
        if len(self.history) < 3:
            return "insufficient data"
        
        recent = self.history[-5:]
        sizes = [p + r for p, r in recent]
        
        # Check for compression
        if all(sizes[i] <= sizes[i-1] for i in range(1, len(sizes))):
            return "compressing"
        # Check for expansion
        elif all(sizes[i] >= sizes[i-1] for i in range(1, len(sizes))):
            return "expanding"
        else:
            return "variable"