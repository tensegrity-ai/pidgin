# Provider APIs

Providers implement the interface between Pidgin and AI model APIs. Each provider handles authentication, rate limiting, and streaming responses.

## Base Provider Interface

All providers inherit from the `Provider` abstract base class:

```python
from pidgin.providers.base import Provider
from typing import List, AsyncGenerator, Optional, Dict
from pidgin.core.types import Message

class Provider(ABC):
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from the model."""
        
    async def cleanup(self) -> None:
        """Clean up provider resources."""
        
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from the last API call."""
```

## Building Providers

Use the provider builder to create provider instances:

```python
from pidgin.providers.builder import build_provider

# Create provider for a specific model
provider = await build_provider("gpt-4")
provider = await build_provider("claude-3-opus")
provider = await build_provider("gemini-1.5-pro")

# Temperature is passed to stream_response, not the builder
response_stream = provider.stream_response(messages, temperature=0.7)
```

## Available Providers

### OpenAI Provider

Supports all OpenAI models including GPT-4 variants.

```python
from pidgin.providers.openai_provider import OpenAIProvider

provider = OpenAIProvider(model="gpt-4")

# Supported models:
# - gpt-4, gpt-4o, gpt-4o-mini
# - gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
# - o3, o3-mini, o4-mini, o4-mini-high
```

**Features:**
- Automatic retry with exponential backoff
- Token usage tracking
- Streaming response support
- Context window truncation

### Anthropic Provider

Supports Claude models from Anthropic.

```python
from pidgin.providers.anthropic import AnthropicProvider

provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")

# Supported models:
# - claude-3-5-sonnet-20241022 (alias: claude, sonnet)
# - claude-3-5-haiku-20241022 (alias: haiku)
# - claude-3-opus-20240229 (alias: opus)
# - claude-4-opus-20250514 (future model)
```

**Features:**
- Automatic retry for rate limits
- Beta header management
- Token usage tracking via headers
- Intelligent context truncation

### Google Provider

Supports Google's Gemini models.

```python
from pidgin.providers.google import GoogleProvider

provider = GoogleProvider(model="gemini-1.5-pro-latest")

# Supported models:
# - gemini-1.5-pro-latest (alias: gemini, gemini-pro)
# - gemini-1.5-flash-latest (alias: gemini-flash)
# - gemini-2.0-flash-exp
```

**Features:**
- Safety settings configuration
- Token counting support
- Streaming with proper error handling
- Automatic retry logic

### xAI Provider

Supports xAI's Grok models.

```python
from pidgin.providers.xai import xAIProvider

provider = xAIProvider(model="grok-2-latest")

# Supported models:
# - grok-2-latest (alias: grok, grok-2)
# - grok-2-mini
```

### Local Provider

Supports local models via Ollama or test models.

```python
from pidgin.providers.local import LocalProvider

# Test model (no API calls)
provider = LocalProvider(model_name="test")

# Ollama models
provider = LocalProvider(model_name="llama3")
provider = LocalProvider(model_name="mistral")
```

## Implementing Custom Providers

Create custom providers by inheriting from the base class:

```python
from pidgin.providers.base import Provider
from typing import List, AsyncGenerator, Optional
import aiohttp

class MyCustomProvider(Provider):
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self.session = None
        self._last_usage = None
    
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Initialize session if needed
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Prepare request
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or 0.7,
            "stream": True
        }
        
        # Make streaming request
        async with self.session.post(
            "https://api.myservice.com/chat",
            headers=headers,
            json=data
        ) as response:
            async for line in response.content:
                # Parse streaming response
                chunk = self._parse_chunk(line)
                if chunk:
                    yield chunk
    
    async def cleanup(self) -> None:
        if self.session:
            await self.session.close()
    
    def get_last_usage(self) -> Optional[Dict[str, int]]:
        return self._last_usage
```

## Provider Configuration

### API Keys

Set API keys via environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."
```

Or programmatically:

```python
from pidgin.providers.api_key_manager import APIKeyManager

APIKeyManager.set_api_key("openai", "sk-...")
APIKeyManager.set_api_key("anthropic", "sk-ant-...")
```

### Context Window Management

Providers automatically handle context truncation:

```python
from pidgin.providers.context_utils import apply_context_truncation

# This happens automatically in providers
truncated = apply_context_truncation(
    messages,
    provider="openai",
    model="gpt-4",
    logger_name=__name__
)
```

### Error Handling

Providers include intelligent error handling:

```python
try:
    async for chunk in provider.stream_response(messages):
        print(chunk, end="")
except Exception as e:
    # Providers convert API errors to friendly messages
    print(f"Error: {e}")
```

Common error types:
- Rate limit errors (automatic retry)
- Authentication errors (check API key)
- Context length errors (automatic truncation)
- Network errors (automatic retry)

## Token Tracking

Track token usage across providers:

```python
from pidgin.providers import get_token_tracker

tracker = get_token_tracker()

# After conversations
usage = tracker.get_usage_by_model()
for model, stats in usage.items():
    print(f"{model}: {stats['total_tokens']} tokens")

# Get total cost estimate
total_cost = tracker.get_total_cost()
print(f"Estimated cost: ${total_cost:.2f}")
```

## Best Practices

1. **Always use the builder**: Use `build_provider()` rather than instantiating directly
2. **Handle cleanup**: Call `cleanup()` when done or use context managers
3. **Monitor token usage**: Check token consumption for cost management
4. **Set appropriate temperatures**: Different models have different optimal ranges
5. **Handle errors gracefully**: Providers throw descriptive exceptions
6. **Use streaming**: All providers support streaming for better UX

## Provider-Specific Features

### OpenAI
- Function calling support (future)
- Embedding models (future)
- Fine-tuned model support

### Anthropic
- System prompts via first message
- Claude-specific formatting
- Vision support (future)

### Google
- Safety settings customization
- Multi-modal support (future)
- Grounding support (future)

### Local/Ollama
- No API keys required
- Custom model support
- Hardware acceleration options