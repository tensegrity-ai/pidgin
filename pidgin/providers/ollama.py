"""Ollama provider for local model inference."""

import json
import logging
import socket
from collections.abc import AsyncGenerator
from typing import List, Optional

import aiohttp

from ..core.types import Message
from .base import Provider
from .error_utils import ProviderErrorHandler

logger = logging.getLogger(__name__)

# Import model config classes from central location
from ..config.model_types import ModelConfig

# Ollama model definitions
OLLAMA_MODELS = {
    "local:qwen": ModelConfig(
        model_id="local:qwen",
        display_name="Qwen",
        aliases=["qwen", "qwen-tiny"],
        provider="local",
        context_window=32768,
        notes="Qwen 0.5B via Ollama - requires Ollama running",
    ),
    "local:phi": ModelConfig(
        model_id="local:phi",
        display_name="Phi",
        aliases=["phi", "phi3"],
        provider="local",
        context_window=4096,
        notes="Phi-3 via Ollama",
    ),
    "local:mistral": ModelConfig(
        model_id="local:mistral",
        display_name="Mistral",
        aliases=["mistral", "mistral7b"],
        provider="local",
        context_window=32768,
        notes="Mistral 7B via Ollama - requires 8GB+ RAM",
    ),
}


class OllamaProvider(Provider):
    """Provider that uses Ollama for local inference."""

    def __init__(self, model_name: str = "qwen2.5:0.5b"):
        super().__init__()
        self.model_name = model_name
        self.base_url = "http://localhost:11434"

        # Set up error handler for Ollama
        self.error_handler = ProviderErrorHandler(
            provider_name="Ollama",
            custom_errors={
                "connection_error": "Cannot connect to Ollama. Start it with: ollama serve",
                "model_not_found": f"Model '{model_name}' not found. Run: ollama pull {model_name}",
                "server_not_running": "Ollama server is not running!\nPlease start it with: ollama serve\nOr run: pidgin chat -a local -b local (to auto-start)",
            },
            custom_suppress=[
                "connection_error",
                "model_not_found",
                "server_not_running",
            ],
        )

        # Check if Ollama is running at initialization
        self._check_ollama_available()

    def _check_ollama_available(self):
        """Check if Ollama server is running."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", 11434))
            sock.close()
            if result != 0:
                raise RuntimeError("server_not_running")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to Ollama: {e}")

    async def stream_response(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama model."""

        # Apply context truncation
        from .context_utils import apply_context_truncation

        truncated_messages = apply_context_truncation(
            messages,
            provider="local",  # Use "local" provider for Ollama models
            model=self.model_name,
            logger_name=__name__,
            allow_truncation=self.allow_truncation,
        )

        # Convert messages to Ollama format
        ollama_messages = []
        for msg in truncated_messages:
            role = "assistant" if msg.role == "assistant" else "user"
            ollama_messages.append({"role": role, "content": msg.content})

        request_data = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": True,
        }

        if temperature is not None:
            request_data["options"] = {"temperature": temperature}

        # Configure timeouts for local model
        timeout = aiohttp.ClientTimeout(
            total=300,  # 5 minutes total timeout
            connect=10,  # 10 seconds to connect to Ollama
            sock_read=60,  # 60 seconds between data chunks
        )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/chat", json=request_data
                ) as response:
                    if response.status == 404:
                        # Model not found error
                        error = Exception("model_not_found")
                        friendly_msg = self.error_handler.get_friendly_error(error)
                        yield f"Error: {friendly_msg}"
                        return

                    elif response.status != 200:
                        error_text = await response.text()
                        yield f"Error: Ollama returned status {response.status}: {error_text}"
                        return

                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line)
                                if "message" in chunk and "content" in chunk["message"]:
                                    yield chunk["message"]["content"]
                            except (json.JSONDecodeError, ValueError, TypeError):
                                # Skip malformed JSON lines
                                pass
        except aiohttp.ClientConnectorError:
            # Connection error
            error = Exception("connection_error")
            friendly_msg = self.error_handler.get_friendly_error(error)
            if self.error_handler.should_suppress_traceback(error):
                logger.info(f"Expected error: {friendly_msg}")
            yield f"Error: {friendly_msg}"
        except Exception as e:
            # Other errors
            friendly_msg = self.error_handler.get_friendly_error(e)
            if self.error_handler.should_suppress_traceback(e):
                logger.info(f"Expected error: {friendly_msg}")
            else:
                logger.error(f"Unexpected error: {e!s}", exc_info=True)
            yield f"Error: {friendly_msg}"
