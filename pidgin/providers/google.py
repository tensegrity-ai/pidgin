import os
from typing import List, AsyncIterator, AsyncGenerator
from ..types import Message
from .base import Provider

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

    async def stream_response(
        self, messages: List[Message]
    ) -> AsyncGenerator[str, None]:
        # Convert to Google format
        # Google uses 'user' and 'model' roles instead of 'user' and 'assistant'
        google_messages = []
        for m in messages:
            role = "model" if m.role == "assistant" else m.role
            google_messages.append({"role": role, "parts": [m.content]})

        try:
            # Create chat session
            chat = self.model.start_chat(history=google_messages[:-1])
            # Stream the response
            response = chat.send_message(google_messages[-1]["parts"][0], stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            # Basic error handling - just don't crash
            raise Exception(f"Google API error: {str(e)}")
