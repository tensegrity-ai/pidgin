# Pidgin Architecture

## Overview

Pidgin is an event-driven system for recording and analyzing AI-to-AI conversations. Every action emits events, providing complete observability while maintaining clean separation of concerns.

## Core Principles

1. **Event-Driven Everything**: All state changes flow through events
2. **Provider Agnostic**: Conductors don't know if responses come from APIs or local models
3. **Observable by Default**: Every interaction can be tracked and analyzed
4. **Modular Components**: Each module has a single, clear responsibility

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│     CLI     │────▶│   Conductor  │────▶│   EventBus  │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                    ┌───────▼────────┐           │
                    │    Providers   │           ▼
                    ├────────────────┤    ┌─────────────┐
                    │ • Anthropic    │    │   Storage   │
                    │ • OpenAI       │    │ • SQLite    │
                    │ • Google       │    │ • JSON      │
                    │ • Ollama       │    │ • Markdown  │
                    │ • Local (test) │    └─────────────┘
                    └────────────────┘
```

## Provider Architecture

All providers implement the same interface:

```python
class Provider(ABC):
    async def stream_response(
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]
```

Provider types:
- **API Providers**: AnthropicProvider, OpenAIProvider, GoogleProvider, xAIProvider
- **Local Providers**: LocalProvider (test model), OllamaProvider

The Conductor doesn't distinguish between provider types - all implement the same streaming interface.

## Local Model Support

Pidgin supports local models through two mechanisms:

### Test Model
- Built-in deterministic model for testing
- No dependencies required
- Available as `local:test`
- Provides consistent responses for development

### Ollama Integration
- External Ollama server handles model management
- Pidgin communicates via HTTP API
- Models: qwen2.5:0.5b, phi3, mistral
- Auto-downloads models on first use
- Automatic installation support with user consent

```
┌─────────────┐     HTTP      ┌──────────────┐
│   Pidgin    │ ──────────▶   │ Ollama Server│
│OllamaProvider│               │ (port 11434) │
└─────────────┘               └──────────────┘
                                     │
                              ┌──────▼────────┐
                              │ Local Models  │
                              │ (GGUF format) │
                              └───────────────┘
```

Ollama installation flow:
1. Detect if Ollama is installed
2. Offer to install if missing (with user consent)
3. Start server automatically if not running
4. Pull models on first use

## Event System

The EventBus is the central nervous system of Pidgin:

```python
# Core events
ConversationStartEvent
TurnStartEvent
MessageRequestEvent
MessageChunkEvent
MessageCompleteEvent
TurnCompleteEvent
ConversationEndEvent

# Metrics events  
ConvergenceCalculatedEvent
MetricsCalculatedEvent

# Error events
APIErrorEvent
RateLimitEvent
```

## Component Responsibilities

### Conductor (`core/conductor.py`)
- Orchestrates conversations between agents
- Manages turn-taking and message flow
- Emits events for all state changes
- Handles interrupts and pausing

### EventBus (`core/event_bus.py`)
- Central event distribution
- Async event handling
- Type-safe event subscriptions
- Zero coupling between components

### Providers (`providers/`)
- Implement streaming interface
- Handle API-specific details
- Emit token usage events
- Manage rate limiting

### Metrics Calculator (`metrics/calculator.py`)
- Subscribes to turn events
- Calculates ~150 metrics per turn
- Emits metrics events
- Single source of truth for all metrics

### Storage (`io/`)
- Subscribes to relevant events
- Persists to SQLite/JSON/Markdown
- No direct coupling to other components

## Experiment System

Experiments run as Unix daemon processes:

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│ CLI Command  │────▶│ Daemon Process│────▶│   EventBus   │
└──────────────┘     └───────────────┘     └──────────────┘
                             │                      │
                     ┌───────▼────────┐    ┌───────▼──────┐
                     │ Parallel Runner│    │ SQLite Store │
                     │ • Rate limiting │    │ • Metrics    │
                     │ • Fault tolerant│    │ • Messages   │
                     │ • Progress track│    │ • Metadata   │
                     └────────────────┘    └──────────────┘
```

## Dependencies

### Core (always required)
- **click**: CLI framework
- **rich**: Terminal UI
- **asyncio**: Async operations (built-in)
- **sqlite3**: Database (built-in)

### Optional
- **aiohttp**: For Ollama communication (when using local models)
- **API provider SDKs**: Only needed for specific providers

This modular approach keeps the base installation minimal (~50MB) while allowing users to add only what they need.

## Data Flow Example

1. User runs: `pidgin chat -a claude -b ollama:qwen`
2. CLI creates Conductor with providers
3. Conductor emits `ConversationStartEvent`
4. Storage components start recording
5. For each turn:
   - Conductor emits `TurnStartEvent`
   - Sends `MessageRequestEvent` to agent
   - Provider streams response chunks
   - Each chunk triggers `MessageChunkEvent`
   - Complete message triggers `MessageCompleteEvent`
   - Metrics calculator computes metrics
   - `TurnCompleteEvent` with metrics emitted
6. Storage components persist all data
7. `ConversationEndEvent` completes the flow

## Extension Points

### Adding a New Provider
1. Implement the `Provider` interface
2. Add to provider factory
3. Add model configurations
4. No other changes needed

### Adding New Metrics
1. Add calculation in `metrics/calculator.py`
2. Add to database schema if needed
3. Metrics automatically flow through events

### Adding Analysis Tools
1. Subscribe to relevant events
2. Process data as needed
3. No core system changes required

## Design Decisions

### Why Event-Driven?
- Complete decoupling between components
- Natural audit trail
- Easy to extend without modifying core
- Enables real-time monitoring

### Why Providers Are Agnostic
- Allows mixing local and API models
- Simplifies testing with deterministic models
- Future-proof for new model sources
- Clean abstraction boundary

### Why SQLite?
- Zero configuration
- Excellent for research datasets
- Built into Python
- Easy to analyze with standard tools

## Performance Considerations

- **Streaming**: All providers stream to minimize latency
- **Async Throughout**: Non-blocking I/O everywhere
- **Lazy Loading**: Models load only when needed
- **Event Batching**: High-frequency events can be batched
- **Rate Limiting**: Automatic backoff and retry logic

## Security Notes

- API keys never logged or stored
- All file I/O respects system permissions
- No network access except to configured endpoints
- Local models run in isolated processes (via Ollama)

---

This architecture enables Pidgin to be both simple to use and powerful to extend, while maintaining complete observability of AI conversation dynamics.