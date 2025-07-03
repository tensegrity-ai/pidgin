import os
import logging
from typing import List, AsyncIterator, AsyncGenerator, Optional, Dict
from ..core.types import Message
from .base import Provider

logger = logging.getLogger(__name__)

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

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Apply context management
        from .context_manager import ProviderContextManager
        context_mgr = ProviderContextManager()
        truncated_messages = context_mgr.prepare_context(
            messages,
            provider="google",
            model=self.model.model_name if hasattr(self.model, 'model_name') else None
        )
        
        # Log if truncation occurred
        if len(truncated_messages) < len(messages):
            logger.info(
                f"Truncated from {len(messages)} to {len(truncated_messages)} messages "
                f"for Google model"
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
            # Basic error handling - just don't crash
            raise Exception(f"Google API error: {str(e)}")
    
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
        return self._last_usage
