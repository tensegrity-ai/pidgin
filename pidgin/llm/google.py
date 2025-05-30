"""Google (Gemini) LLM implementation."""
import os
from typing import List, Union, AsyncIterator, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from pidgin.llm.base import LLM, LLMConfig, Message, LLMResponse


class GoogleLLM(LLM):
    """Google Gemini implementation."""
    
    MODELS = {
        "gemini-pro": {"name": "Gemini Pro", "max_tokens": 32768},
        "gemini-pro-vision": {"name": "Gemini Pro Vision", "max_tokens": 32768},
    }
    
    def __init__(self, config: LLMConfig, api_key: Optional[str] = None):
        super().__init__(config, api_key)
        
        # Get API key
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided")
        
        # Configure API
        genai.configure(api_key=self.api_key)
        
        # Validate model
        if config.model not in self.MODELS:
            raise ValueError(f"Unknown Google model: {config.model}")
        
        # Initialize model
        generation_config = genai.GenerationConfig(
            temperature=config.temperature or 0.7,
            top_p=config.top_p or 0.95,
            max_output_tokens=config.max_tokens or self.MODELS[config.model]["max_tokens"],
        )
        
        # Safety settings - set to be permissive for research
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        self.model = genai.GenerativeModel(
            model_name=config.model,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
    
    @property
    def provider(self) -> str:
        return "google"
    
    async def generate(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncIterator[str]]:
        """Generate response from Gemini."""
        # Prepare messages
        prepared_messages = self.prepare_messages(messages)
        
        # Convert to Gemini format
        # Gemini uses a different conversation format
        chat = self.model.start_chat(history=[])
        
        # Add system prompt as first user message if present
        gemini_messages = []
        for msg in prepared_messages:
            if msg.role == "system":
                # Prepend system message to first user message
                gemini_messages.append({
                    "role": "user",
                    "parts": [msg.content]
                })
                gemini_messages.append({
                    "role": "model",
                    "parts": ["I understand. I'll follow these instructions."]
                })
            elif msg.role == "user":
                gemini_messages.append({
                    "role": "user",
                    "parts": [msg.content]
                })
            elif msg.role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [msg.content]
                })
        
        # Set chat history
        if len(gemini_messages) > 1:
            chat.history = gemini_messages[:-1]
        
        # Get the last user message
        last_message = gemini_messages[-1]["parts"][0] if gemini_messages else ""
        
        if stream:
            return self._stream_response(chat, last_message)
        else:
            return await self._generate_response(chat, last_message)
    
    async def _generate_response(self, chat, message: str) -> LLMResponse:
        """Generate a complete response."""
        # Note: Google's Python SDK doesn't have native async support yet
        # We'll use sync version for now
        response = await self._run_sync(chat.send_message, message)
        
        # Extract content
        content = response.text if hasattr(response, 'text') else ""
        
        # Build usage info (Gemini doesn't provide detailed token counts)
        usage = {
            "prompt_tokens": self.count_tokens(message),
            "completion_tokens": self.count_tokens(content),
            "total_tokens": 0
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        
        return LLMResponse(
            content=content,
            model=self.config.model,
            usage=usage,
            metadata={
                "safety_ratings": response.safety_ratings if hasattr(response, 'safety_ratings') else None,
            }
        )
    
    async def _stream_response(self, chat, message: str) -> AsyncIterator[str]:
        """Stream response tokens."""
        # Note: Streaming with Google's SDK requires sync iteration
        response = await self._run_sync(chat.send_message, message, stream=True)
        
        for chunk in response:
            if hasattr(chunk, 'text'):
                yield chunk.text
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous function in async context."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def validate_connection(self) -> bool:
        """Validate Google API connection."""
        try:
            # Try a minimal API call
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Hi")
            return bool(response.text)
        except Exception:
            return False
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for Gemini models."""
        # Gemini uses different tokenization
        # Rough estimate for now
        return len(text) // 4