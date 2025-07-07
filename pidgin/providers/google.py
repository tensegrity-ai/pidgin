import os
import logging
from typing import List, AsyncIterator, AsyncGenerator, Optional, Dict
from ..core.types import Message
from .base import Provider
from .error_utils import create_google_error_handler

logger = logging.getLogger(__name__)

# Import model config classes from central location
from ..config.models import ModelConfig, ModelCharacteristics

# Google model definitions
GOOGLE_MODELS = {
    "gemini-2.0-flash-exp": ModelConfig(
        model_id="gemini-2.0-flash-exp",
        shortname="Flash",
        aliases=["gemini-flash", "flash", "gemini"],
        provider="google",
        context_window=1048576,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=4,
            avg_response_length="short",
            recommended_pairings=["gpt-4.1-nano", "gemini-2.0-flash-exp"],
            conversation_style="concise",
        ),
        notes="Latest and fastest Gemini model",
    ),
    "gemini-2.0-flash-thinking-exp": ModelConfig(
        model_id="gemini-2.0-flash-thinking-exp",
        shortname="Thinking",
        aliases=["gemini-thinking", "thinking", "flash-thinking"],
        provider="google",
        context_window=32767,
        pricing_tier="standard",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["o3", "claude-4-opus-20250514"],
            conversation_style="analytical",
        ),
        notes="Reasoning-focused Gemini model",
    ),
    "gemini-exp-1206": ModelConfig(
        model_id="gemini-exp-1206",
        shortname="Gemini-Exp",
        aliases=["gemini-exp", "exp-1206"],
        provider="google",
        context_window=2097152,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=8,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="verbose",
        ),
        notes="Experimental Gemini with 2M context",
    ),
    "gemini-1.5-pro": ModelConfig(
        model_id="gemini-1.5-pro",
        shortname="Gemini-Pro",
        aliases=["gemini-pro", "1.5-pro"],
        provider="google",
        context_window=2097152,
        pricing_tier="premium",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="medium",
            recommended_pairings=["gpt-4o", "claude-4-sonnet-20250514"],
            conversation_style="verbose",
        ),
        notes="Production Gemini with 2M context",
    ),
    "gemini-1.5-flash": ModelConfig(
        model_id="gemini-1.5-flash",
        shortname="Flash-1.5",
        aliases=["flash-1.5"],
        provider="google",
        context_window=1048576,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=3,
            avg_response_length="short",
            recommended_pairings=["gpt-4o-mini", "claude-3-5-haiku-20241022"],
            conversation_style="concise",
        ),
        notes="Fast Gemini 1.5 model",
    ),
    "gemini-1.5-flash-8b": ModelConfig(
        model_id="gemini-1.5-flash-8b",
        shortname="Flash-8B",
        aliases=["flash-8b", "gemini-8b"],
        provider="google",
        context_window=1048576,
        pricing_tier="economy",
        characteristics=ModelCharacteristics(
            verbosity_level=2,
            avg_response_length="short",
            recommended_pairings=["gpt-4.1-nano", "gemini-1.5-flash-8b"],
            conversation_style="concise",
        ),
        notes="Smallest Gemini model",
    ),
}

try:
    import google.generativeai as genai

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    genai = None


class GoogleProvider(Provider):
    def __init__(self, model: str):
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google Generative AI not available. Install with: "
                "pip install google-generativeai"
            )

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable not set. "
                "Please set it to your Google AI API key."
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self._last_usage = None
        self.error_handler = create_google_error_handler()

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Apply context truncation
        from .context_utils import apply_context_truncation
        
        truncated_messages = apply_context_truncation(
            messages,
            provider="google",
            model=self.model.model_name if hasattr(self.model, 'model_name') else None,
            logger_name=__name__
        )
        
        # Convert to Google format
        # Google uses 'user' and 'model' roles instead of 'user' and 'assistant'
        google_messages = []
        for m in truncated_messages:
            role = "model" if m.role == "assistant" else m.role
            google_messages.append({"role": role, "parts": [m.content]})

        try:
            # Reset usage tracking
            self._last_usage = None
            
            # Create chat session
            chat = self.model.start_chat(history=google_messages[:-1])
            
            # Build generation config if temperature is specified
            generation_config = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            
            # Stream the response
            response = chat.send_message(
                google_messages[-1]["parts"][0], 
                stream=True,
                generation_config=generation_config if generation_config else None
            )

            last_chunk = None
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                last_chunk = chunk
            
            # Try to extract usage data from the last chunk
            if last_chunk and hasattr(last_chunk, 'usage_metadata'):
                metadata = last_chunk.usage_metadata
                if metadata:
                    self._last_usage = {
                        'prompt_tokens': getattr(metadata, 'prompt_token_count', 0),
                        'completion_tokens': getattr(metadata, 'candidates_token_count', 0),
                        'total_tokens': getattr(metadata, 'total_token_count', 0)
                    }
        except Exception as e:
            # Get friendly error message
            friendly_error = self.error_handler.get_friendly_error(e)
            
            # Log appropriately based on error type
            if self.error_handler.should_suppress_traceback(e):
                logger.info(f"Expected API error: {friendly_error}")
            else:
                logger.error(f"Unexpected API error: {str(e)}", exc_info=True)
            
            # Create a clean exception with friendly message
            raise Exception(friendly_error) from None
    
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
