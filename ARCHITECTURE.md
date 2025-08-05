# Pidgin Architecture

## Overview

Pidgin is an event-driven system for conducting and recording AI-to-AI conversations. Every action emits events, providing complete observability while maintaining clean separation of concerns.

## Core Principles

1. **Event-Driven Everything**: All state changes flow through events
2. **Provider Agnostic**: Conductors don't know if responses come from APIs or local models
3. **Observable by Default**: Every interaction can be tracked and analyzed
4. **Modular Components**: Each module has a single, clear responsibility (<300 lines per module)
5. **JSONL-First Storage**: Append-only logs as the source of truth

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│     CLI     │────▶│   Conductor  │────▶│   EventBus  │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                    │
                    ┌───────▼────────┐           │
                    │     Router     │           ▼
                    │ (msg transform)│    ┌─────────────────┐
                    └───────┬────────┘    │  TrackingBus    │
                            │             │  (experiments)  │
                    ┌───────▼────────┐    └────────┬────────┘
                    │    Providers   │             │
                    ├────────────────┤             ▼
                    │ • Anthropic    │    ┌─────────────────┐
                    │ • OpenAI       │    │     Storage     │
                    │ • Google       │    ├─────────────────┤
                    │ • xAI          │    │ • JSONL (live)  │
                    │ • Ollama       │    │ • manifest.json │
                    │ • Local (test) │    │ • DuckDB (post) │
                    └────────────────┘    └─────────────────┘
```

## Core Components

### Conductor (`core/conductor.py`)
Orchestrates conversations between agents. Modularized into:
- `interrupt_handler.py` - Interrupt and pause management
- `name_coordinator.py` - Agent naming and identity
- `turn_executor.py` - Turn execution logic
- `message_handler.py` - Message processing
- `conversation_lifecycle.py` - Start/end lifecycle events

### Router (`core/router.py`)
Critical component that transforms messages for each agent's perspective:
- Converts messages between user/assistant roles
- Manages conversation history for each agent
- Handles message truncation for context limits
- Ensures each agent sees the correct perspective

### EventBus (`core/event_bus.py`)
Central event distribution system:
- Type-safe event subscriptions
- Async event handling
- Zero coupling between components
- Supports multiple subscribers per event type

### TrackingEventBus (`experiments/tracking_event_bus.py`)
Specialized event bus for experiment tracking:
- Writes events to JSONL files
- Updates manifest.json in real-time
- Tracks token usage per agent
- Manages conversation state

## Provider Architecture

All providers implement the same interface:

```python
class Provider(ABC):
    async def stream_response(
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]
```

### EventAwareProvider Wrapper
All providers are wrapped with `EventAwareProvider` which:
- Subscribes to `MessageRequestEvent` for their agent
- Emits `MessageCompleteEvent` when done
- Tracks token usage via `TokenUsageEvent`
- Handles API errors gracefully

Provider types:
- **API Providers**: Anthropic, OpenAI, Google, xAI
- **Local Providers**: LocalProvider (test), OllamaProvider

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
- Models: qwen2.5:0.5b, phi3, mistral, llama3.2
- Auto-downloads models on first use
- Automatic installation support with user consent

```
┌──────────────┐     HTTP      ┌──────────────┐
│   Pidgin     │ ────────────▶ │ Ollama Server│
│OllamaProvider│               │ (port 11434) │
└──────────────┘               └──────────────┘
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

## Data Flow Architecture (JSONL-First)

Pidgin uses a JSONL-first architecture that eliminates database contention:

```
┌──────────────┐
│ Conversation │
└──────┬───────┘
       │
       ▼ (real-time)
┌──────────────┐     ┌─────────────┐
│    JSONL     │────▶│  manifest   │
│   (append)   │     │   .json     │
└──────┬───────┘     └─────────────┘
       │
       ▼ (post-experiment)
┌──────────────┐     ┌─────────────┐
│PostProcessor │────▶│   DuckDB    │
│              │     │  (analysis) │
└──────┬───────┘     └─────────────┘
       │
       ▼ (generated)
┌─────────────────────────┐
│ • Transcripts (.md)     │
│ • README.md             │
│ • Jupyter Notebooks     │
└─────────────────────────┘
```

### Key Benefits:
- **No lock contention**: JSONL files are append-only
- **Complete observability**: Every event recorded and accessible
- **Instant monitoring**: manifest.json provides efficient state
- **Standard tools**: Use tail, grep, jq for debugging
- **Batch import**: Load to DuckDB when convenient
- **Reproducible analysis**: Generate notebooks and transcripts on-demand

### Data Processing Pipeline:
1. **Record**: Conversations emit events to JSONL files in real-time
2. **Track**: Manifest.json provides real-time state for monitoring
3. **Orchestrate**: PostProcessor manages post-experiment processing queue
4. **Import**: EventStore imports JSONL to DuckDB (only DB interface)
5. **Generate**: Create transcripts and notebooks using EventStore data

### File Structure:
```
pidgin_output/
├── experiments/
│   ├── experiment_[id]_[name]_[date]/
│   │   ├── manifest.json           # Real-time state
│   │   ├── conv_[id]_events.jsonl  # Event stream
│   │   ├── README.md               # Auto-generated
│   │   ├── post_processing.log     # Processing log
│   │   └── transcripts/            # Human-readable
│   │       ├── conv_[id].md
│   │       └── summary.md
│   ├── active/
│   │   └── exp_[id].pid           # Daemon PID
│   ├── logs/
│   │   └── experiment_[id].log    # Debug logs
│   └── experiments.duckdb         # Analysis database
```

## Experiment System

### Runner (`experiments/runner.py`)
Manages experiment execution:
- Sequential execution by default (rate limit aware)
- Handles multiple conversations
- Graceful error recovery
- Progress tracking via manifest

### ManifestManager (`experiments/manifest.py`)
Real-time experiment state:
- Atomic updates to manifest.json
- Tracks conversation status
- Records token usage
- Thread-safe operations

### PostProcessor (`experiments/post_processor.py`)
Post-experiment processing pipeline:
- FIFO queue for sequential processing
- Orchestrates all post-processing steps
- Calls EventStore for JSONL import
- Generates transcripts and README files
- Runs after experiment completion

### EventStore (`database/event_store.py`)
Single interface to DuckDB database:
- **Exclusive DB access**: No other component accesses DuckDB directly
- Imports JSONL files to database tables
- Provides repository pattern for data access
- Used by analysis tools and notebook generation
- Enforces data integrity and consistency

## Monitor System

### Monitor (`monitor/monitor.py`)
Core monitor loop (137 lines) that coordinates:

### Display Components
- `display_builder.py` - Main display coordination
- `conversation_panel_builder.py` - Conversation details
- `error_panel_builder.py` - Error tracking display

### Data Components
- `experiment_reader.py` - Reads experiment states
- `metrics_calculator.py` - Calculates tokens and costs
- `error_tracker.py` - Tracks and analyzes errors
- `file_reader.py` - Efficient file operations

## Message Flow and Memory Management

The Router is critical for proper message handling:

- **Message Transformation**: Each agent sees the conversation from their perspective (their messages as "assistant", other's as "user")
- **Context Truncation**: Providers automatically truncate messages to fit their context windows
- **Memory Efficiency**: Only recent messages need to be kept in memory since all messages are stored in JSONL files
- **Token Accuracy**: Token tracking is based on truncated messages sent to APIs, not the full history

This transformation is essential - without it, agents would see incorrect role assignments and conversations would fail.

## Advanced Features

### Conversation Branching
- Branch from any turn in existing conversations
- Create alternate timelines
- Compare different conversation paths
- Useful for testing different prompts

### Dimensions System
- Apply semantic dimensions to conversations
- Generate variations (e.g., formal/casual, technical/simple)
- Create controlled experiments
- Study linguistic variation

### Custom Awareness
- Configure what agents know about the conversation
- Options: none, basic, full, custom
- Control meta-conversation awareness
- Enable self-referential discussions

## Event Types

### Core Events
- `ConversationStartEvent` - Conversation begins
- `TurnStartEvent` - Turn begins
- `MessageRequestEvent` - Request to provider
- `MessageCompleteEvent` - Response complete
- `TurnCompleteEvent` - Turn ends with metrics
- `ConversationEndEvent` - Conversation ends

### Tracking Events
- `TokenUsageEvent` - Token usage per provider
- `ConvergenceWarningEvent` - High convergence detected
- `ContextLimitEvent` - Context window exceeded
- `ExperimentCompleteEvent` - Experiment finished

### Error Events
- `APIErrorEvent` - Provider API errors
- `RateLimitEvent` - Rate limit hit
- `ErrorEvent` - General errors

## Module Size Guidelines

Per CLAUDE.md development guidelines:
- **Ideal**: <200 lines
- **Acceptable**: <300 lines  
- **Must refactor**: >500 lines

Current architecture achieves this through aggressive modularization.

## Extension Points

### Adding a New Provider
1. Implement the `Provider` interface
2. Add to `provider_factory.py`
3. Add model configurations to `model_types.py`
4. Provider automatically wrapped with events

### Adding New Metrics
1. Add calculation in `metrics/calculator.py`
2. Metrics flow through `TurnCompleteEvent`
3. Automatically stored in JSONL and DuckDB

### Adding Analysis Tools
1. Subscribe to relevant events
2. Process data from JSONL files
3. Generate output in post-processing

## Dependencies

### Core (always required)
- **click**: CLI framework
- **rich**: Terminal UI and formatting
- **asyncio**: Async operations (built-in)
- **duckdb**: Analytical database
- **aiofiles**: Async file operations

### Provider-specific
- **anthropic**: Claude models
- **openai**: GPT models
- **google-generativeai**: Gemini models
- **aiohttp**: Ollama and xAI support

## Data Flow Example

1. User runs: `pidgin chat -a claude -b gpt`
2. CLI creates Conductor with providers
3. Conductor emits `ConversationStartEvent`
4. TrackingEventBus starts writing to JSONL
5. For each turn:
   - Conductor emits `TurnStartEvent`
   - Router transforms messages for agent's perspective
   - Sends `MessageRequestEvent` to agent
   - Provider streams response chunks
   - Complete message triggers `MessageCompleteEvent`
   - Metrics calculator computes ~150 metrics
   - `TurnCompleteEvent` with metrics emitted
6. All events written to JSONL files
7. Manifest updated in real-time
8. `ConversationEndEvent` completes the flow
9. PostProcessor imports to DuckDB
10. Transcripts and README generated

## Performance Considerations

### Sequential by Default
- Experiments run sequentially to respect rate limits
- Parallel execution available but not recommended
- Better reliability and reproducibility

### Memory Management
- Only recent messages kept in memory
- Full history in JSONL files
- Streaming responses to minimize memory
- Efficient manifest updates

### Token Optimization
- Automatic context truncation
- Token counting per provider
- Cost tracking in real-time
- Efficient batching strategies

