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
                    │ • OpenAI       │    │ • DuckDB    │
                    │ • Google       │    │ • JSON      │
                    │ • xAI          │    │ • Markdown  │
                    │ • Ollama       │    └─────────────┘
                    │ • Local (test) │
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
- Modularized into focused components:
  - `interrupt_handler.py` - Interrupt management
  - `name_coordinator.py` - Agent naming logic
  - `turn_executor.py` - Turn execution
  - `message_handler.py` - Message processing
  - `conversation_lifecycle.py` - Lifecycle events

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
- DuckDB migration planned for better analytics

## Experiment System

Experiments run as Unix daemon processes:

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│ CLI Command  │────▶│ Daemon Process│────▶│   EventBus   │
└──────────────┘     └───────────────┘     └──────────────┘
                             │                      │
                     ┌───────▼────────┐    ┌───────▼──────┐
                     │ Sequential     │    │ SQLite Store │
                     │ Runner         │    │ • Metrics    │
                     │ • Rate aware   │    │ • Messages   │
                     │ • Fault tolerant│   │ • Metadata   │
                     │ • Progress track│    │ • Events     │
                     └────────────────┘    └──────────────┘
```

**Important Note**: While the architecture supports parallel execution, experiments run sequentially by default due to:
- API provider rate limits
- Local model hardware constraints
- Better reliability and reproducibility

Users can increase parallelism if their environment supports it, but sequential execution is the sensible default.

## Dependencies

### Core (always required)
- **click**: CLI framework
- **rich**: Terminal UI
- **asyncio**: Async operations (built-in)
- **aiosqlite**: Async SQLite (current)
- **duckdb**: Analytical database (planned migration)

### Optional
- **aiohttp**: For Ollama communication (when using local models)
- **API provider SDKs**: Only needed for specific providers

This modular approach keeps the base installation minimal while allowing users to add only what they need.

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
- Simplifies testing and debugging

### Why Providers Are Agnostic
- Allows mixing local and API models
- Simplifies testing with deterministic models
- Future-proof for new model sources
- Clean abstraction boundary

### Why SQLite (currently)?
- Simple, reliable, single-file database
- Good for transactional workloads
- Well-tested async support

### Why DuckDB (planned)?
- Optimized for analytical queries
- Columnar storage for metrics data
- Single file, zero configuration
- Excellent pandas integration
- Perfect for research workloads

### Why Sequential Execution?
- Rate limits make parallel execution problematic
- Hardware constraints for local models
- Better reproducibility for research
- Architecture supports parallel when feasible

## Performance Considerations

- **Streaming**: All providers stream to minimize latency
- **Async Throughout**: Non-blocking I/O everywhere
- **Lazy Loading**: Models load only when needed
- **Sequential Execution**: Avoids rate limit issues
- **SQLite**: Current storage, adequate for experiments
- **DuckDB (planned)**: Will enable fast analytical queries

## Security Notes

- API keys never logged or stored
- All file I/O respects system permissions
- No network access except to configured endpoints
- Local models run in isolated processes (via Ollama)

---

This architecture enables Pidgin to be both simple to use and powerful to extend, while maintaining complete observability of AI conversation dynamics without unnecessary complexity.