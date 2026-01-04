# Pidgin Architecture

## Overview

Pidgin is an event-driven system for conducting and recording AI-to-AI conversations. Every action emits events, providing complete observability while maintaining clean separation of concerns.

## Core Principles

1. **Event-Driven Everything**: All state changes flow through events
2. **Provider Agnostic**: Conductors don't know if responses come from APIs or local models
3. **Observable by Default**: Every interaction can be tracked and analyzed
4. **Modular Components**: Each module has a single, clear responsibility (<300 lines per module)
5. **JSONL-First Storage**: Append-only logs as the source of truth
6. **Repository Pattern**: Database access exclusively through repository layer

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
                    │ • OpenAI       │    │  JSONL Storage  │
                    │ • Google       │    │ + manifest.json │
                    │ • xAI          │    └────────┬────────┘
                    │ • Ollama       │             │ (post-exp)
                    │ • Local (test) │    ┌────────▼────────┐
                    └────────────────┘    │   EventStore   │
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  Repositories   │
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │     DuckDB      │
                                          └─────────────────┘
```

## Core Components

### Conductor (`core/conductor.py`)
Orchestrates conversations between agents. Supporting modules:
- `interrupt_handler.py` - Interrupt and pause management
- `name_coordinator.py` - Agent naming and identity  
- `turn_executor.py` - Turn execution logic
- `message_handler.py` - Message processing
- `conversation_lifecycle.py` - Start/end lifecycle events (split into 3 modules)
- `conversation_setup.py` - Initialization logic
- `conversation_state.py` - State management

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
@dataclass
class ResponseChunk:
    content: str
    chunk_type: Literal["thinking", "response"] = "response"

class Provider(ABC):
    async def stream_response(
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]
```

The `ResponseChunk` dataclass distinguishes between reasoning traces (`chunk_type="thinking"`) and final output (`chunk_type="response"`).

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

## Extended Thinking Support

Pidgin supports extended thinking (reasoning traces) for models that expose their internal reasoning process:

### CLI Options
- `--think` - Enable extended thinking for both agents
- `--think-a` / `--think-b` - Enable for specific agent
- `--thinking-budget N` - Maximum tokens for reasoning (default: 10000)

### How It Works
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Provider   │────▶│ResponseChunk │────▶│   Display    │
│ (streaming)  │     │ type=thinking│     │  (collapsible│
└──────────────┘     │ type=response│     │   panel)     │
                     └──────────────┘     └──────────────┘
                            │
                     ┌──────▼──────┐
                     │ Thinking    │
                     │ Complete    │
                     │ Event       │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │ Thinking    │
                     │ Repository  │
                     └─────────────┘
```

### Provider Support
- **Anthropic**: Full support via `thinking` block in API
- **Other providers**: Not currently supported (thinking params ignored)

### Events
- `ThinkingCompleteEvent` - Emitted when reasoning phase completes, captures full thinking trace
- Stored in database via `ThinkingRepository` for later analysis

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
Orchestrator for database operations:
- **Public API**: External components only interact with EventStore
- **Repository delegation**: EventStore delegates to specialized repositories
- **No direct DB access**: Components outside database package cannot import duckdb
- Coordinates JSONL imports and data access
- Used by analysis tools and notebook generation

### Repository Layer (`database/`)
Specialized data access components:
- `ExperimentRepository` - Experiment CRUD operations
- `ConversationRepository` - Conversation data access
- `MessageRepository` - Message operations
- `MetricsRepository` - Metrics queries and calculations
- `ThinkingRepository` - Thinking trace storage and retrieval
- `EventRepository` - Event storage and querying
- `BaseRepository` - Shared connection and query logic

All database access flows through: External Component → EventStore → Repository → DuckDB

### State Management (`experiments/state/`)
Efficient state reconstruction from JSONL files:
- `manifest_parser.py` - Parses manifest.json for experiment state
- `conversation_parser.py` - Parses conversation events from JSONL
- Used by monitor and analysis tools for efficient state access without database queries

## IO Components (`io/`)

Handles file I/O operations:
- `event_deserializer.py` - Deserializes JSONL events to Event dataclasses
- `jsonl_reader.py` - Efficient reading of experiment JSONL files
- `paths.py` - Path resolution utilities
- `directories.py` - Directory management and creation
- `output_manager.py` - Manages experiment output directories

## Analysis (`analysis/`)

Post-experiment analysis tools:
- `notebook_generator.py` - Auto-generates Jupyter notebooks for experiment analysis
- `notebook_cells.py` - Cell definitions (setup, visualization, statistics, convergence)
- `convergence.py` - Convergence analysis utilities

## Monitor System

### Monitor (`monitor/monitor.py`)
Core monitor loop that coordinates:

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

### Custom Awareness
- Configure what agents know about the conversation
- Options: none, basic, firm, research, backrooms, custom
- Control meta-conversation awareness
- Enable self-referential discussions
- `backrooms` preset inspired by liminalbardo for liminal AI exploration

## Event Types

All events inherit from the base `Event` class with `timestamp` and `event_id` fields.

### Core Events
- `ConversationStartEvent` - Conversation begins with agent config
- `ConversationEndEvent` - Conversation ends with status
- `TurnStartEvent` - Turn begins
- `TurnCompleteEvent` - Turn ends with metrics
- `MessageRequestEvent` - Request to provider (includes thinking params)
- `MessageChunkEvent` - Streaming chunk with timing
- `MessageCompleteEvent` - Response complete with token counts
- `SystemPromptEvent` - System prompt delivery to agent

### Thinking Events
- `ThinkingCompleteEvent` - Extended thinking trace captured

### Control Flow Events
- `InterruptRequestEvent` - User or system interrupt
- `ConversationPausedEvent` - Conversation paused
- `ConversationResumedEvent` - Conversation resumed
- `ConversationBranchedEvent` - Branched from another conversation

### Tracking Events
- `TokenUsageEvent` - Token usage per provider
- `ContextTruncationEvent` - Messages truncated for context window
- `ContextLimitEvent` - Context window limit reached
- `RateLimitPaceEvent` - Rate limit pacing applied
- `ExperimentCompleteEvent` - Experiment finished

### Post-Processing Events
- `PostProcessingStartEvent` - Processing pipeline begins
- `PostProcessingCompleteEvent` - Processing pipeline ends

### Error Events
- `ErrorEvent` - General errors
- `APIErrorEvent` - Provider API errors with retry info
- `ProviderTimeoutEvent` - Provider timeout

## Module Design Philosophy

### Single Responsibility Principle
While we aim for smaller modules (<300 lines), some core orchestration components are necessarily longer when they have a single, focused responsibility. Examples include:
- **EventStore**: Central database orchestrator managing all repository interactions
- **Conductor**: Core conversation orchestrator coordinating multiple subsystems

These larger orchestration modules remain cohesive despite their size because they:
- Have one clear purpose
- Don't mix concerns (e.g., orchestration vs implementation)
- Delegate specific tasks to focused helper modules
- Act as coordination points rather than implementing details

### Modularization Strategy
For complex functionality, we split into:
- **Orchestrator**: Coordinates the overall process
- **Helpers**: Handle specific aspects (e.g., `interrupt_handler.py`, `turn_executor.py`)
- **Services**: Provide reusable functionality
- **Repositories**: Manage data access patterns

## Extension Points

### Adding a New Provider
1. Implement the `Provider` interface
2. Add to `providers/builder.py`
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

