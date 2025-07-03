"""Ollama provider for local model inference."""
import json
import socket
from typing import List, Optional, AsyncGenerator
import aiohttp
from .base import Provider
from ..core.types import Message

# Import model config classes from central location
from ..config.models import ModelConfig, ModelCharacteristics

# Ollama model definitions
OLLAMA_MODELS = {
    "local:qwen": ModelConfig(
        model_id="local:qwen",
        shortname="Qwen-0.5B",
        aliases=["qwen", "qwen-tiny"],
        provider="local",
        context_window=32768,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=4,
            avg_response_length="short",
            recommended_pairings=["local:phi", "local:test"],
            conversation_style="concise",
        ),
        notes="Qwen 0.5B via Ollama - requires Ollama running",
    ),
    "local:phi": ModelConfig(
        model_id="local:phi",
        shortname="Phi-3",
        aliases=["phi", "phi3"],
        provider="local",
        context_window=4096,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=6,
            avg_response_length="medium",
            recommended_pairings=["local:qwen", "local:test"],
            conversation_style="analytical",
        ),
        notes="Phi-3 via Ollama",
    ),
    "local:mistral": ModelConfig(
        model_id="local:mistral",
        shortname="Mistral-7B",
        aliases=["mistral", "mistral7b"],
        provider="local",
        context_window=32768,
        pricing_tier="free",
        characteristics=ModelCharacteristics(
            verbosity_level=7,
            avg_response_length="long",
            recommended_pairings=["claude-4-opus-20250514", "gpt-4.1"],
            conversation_style="verbose",
        ),
        notes="Mistral 7B via Ollama - requires 8GB+ RAM",
    ),
}


class OllamaProvider(Provider):
    """Provider that uses Ollama for local inference."""
    
    def __init__(self, model_name: str = "qwen2.5:0.5b"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
        
        # Check if Ollama is running at initialization
        self._check_ollama_available()
    
    def _check_ollama_available(self):
        """Check if Ollama server is running."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 11434))
            sock.close()
            if result != 0:
                raise RuntimeError(
                    "Ollama server is not running!\n"
                    "Please start it with: ollama serve\n"
                    "Or run: pidgin chat -a local -b local (to auto-start)"
                )
        except Exception as e:
            raise RuntimeError(f"Cannot connect to Ollama: {e}")
        
    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama model."""
        
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
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
            total=300,      # 5 minutes total timeout
            connect=10,     # 10 seconds to connect to Ollama
            sock_read=60    # 60 seconds between data chunks
        )
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                ) as response:
                    if response.status == 404:
                        yield f"Error: Model '{self.model_name}' not found in Ollama"
                        yield f"Run: ollama pull {self.model_name}"
                        return
                        
                    elif response.status != 200:
                        error_text = await response.text()
                        yield f"Error: Ollama returned status {response.status}: {error_text}"
                        return
                        
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line)
                                if 'message' in chunk and 'content' in chunk['message']:
                                    yield chunk['message']['content']
                            except:
                                pass
        except aiohttp.ClientConnectorError:
            yield "Error: Cannot connect to Ollama. Start it with: ollama serve"
        except Exception as e:
            yield f"Error: {str(e)}"