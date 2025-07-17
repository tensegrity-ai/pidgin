# Pidgin Architecture

A comprehensive guide to Pidgin's design philosophy, system architecture, and implementation details.

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [System Overview](#system-overview)
3. [Core Architecture](#core-architecture)
4. [Data Architecture](#data-architecture)
5. [Event-Driven Design](#event-driven-design)
6. [Provider Architecture](#provider-architecture)
7. [Experiment System](#experiment-system)
8. [Metrics & Analysis](#metrics--analysis)
9. [Extension Points](#extension-points)
10. [Design Decisions](#design-decisions)

## Design Philosophy

Pidgin is built on four foundational principles:

### 1. **Observability First**
Every interaction between AI models should be recordable, reproducible, and analyzable. We achieve this through comprehensive event logging where every state change, message, and decision flows through a central event bus.

### 2. **Provider Agnostic**
The system doesn't care whether responses come from OpenAI, Anthropic, local models, or even deterministic test implementations. All providers implement the same streaming interface, allowing seamless mixing of different models.

### 3. **Research-Oriented**
Built for researchers studying AI communication patterns, not for production chatbots. This drives decisions like:
- Comprehensive metrics (150+ per turn)
- Complete event logs over performance optimization
- Reproducibility over throughput
- Sequential execution for rate limit friendliness

### 4. **Simple But Not Simplistic**
The CLI should be dead simple (`pidgin run -a claude -b gpt -t 10`) while the underlying system captures rich data for analysis. Power users can dive deep, but casual users aren't overwhelmed.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Interface                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│       CLI       │   Python API    │         Experiments         │
└────────┬────────┴────────┬────────┴──────────┬──────────────────┘
         │                 │                   │
         └─────────────────┴───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Conductor   │    Orchestrates conversations
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Event Bus   │    Central nervous system
                    └───┬─────┬───┘
                        │     │
              ┌─────────┴──┐  └─────────────┐
              │            │                │
        ┌─────▼────┐ ┌─────▼────┐    ┌─────▼─────┐
        │Providers │ │ Storage  │    │ Analysis  │
        ├──────────┤ ├──────────┤    ├───────────┤
        │• Claude  │ │• JSONL   │    │• Metrics  │
        │• GPT     │ │• DuckDB  │    │• Patterns │
        │• Local   │ │• Markdown│    │• Jupyter  │
        └──────────┘ └──────────┘    └───────────┘
```

## Core Architecture

### The Conductor Pattern

The Conductor is the maestro of conversations, but it knows surprisingly little:
- Doesn't know which models are being used
- Doesn't know how messages are stored
- Doesn't know what metrics are calculated

Instead, it simply:
1. Manages turn-taking between agents
2. Routes messages through providers
3. Emits events for everything that happens

```python
# Simplified Conductor flow
async def run_turn(self):
    await self.bus.emit(TurnStartEvent(turn_number=self.turn))
    
    # Get response from agent A
    message_a = await self.get_agent_response(self.agent_a)
    await self.bus.emit(MessageCompleteEvent(message_a))
    
    # Get response from agent B
    message_b = await self.get_agent_response(self.agent_b)
    await self.bus.emit(MessageCompleteEvent(message_b))
    
    await self.bus.emit(TurnCompleteEvent(turn_number=self.turn))
```

### Component Isolation

Each major component is isolated and communicates only through events:

```
┌─────────────┐     Events      ┌─────────────┐
│  Component  │ ───────────────▶ │  Event Bus  │
│      A      │                  │             │
└─────────────┘                  └──────┬──────┘
                                        │
┌─────────────┐     Events             │
│  Component  │ ◀───────────────────────┘
│      B      │
└─────────────┘

Components never directly call each other
```

This isolation enables:
- Easy testing (mock the event bus)
- Simple extensions (just subscribe to events)
- Clear debugging (follow the event trail)
- Zero coupling between components

## Data Architecture

### JSONL-First Design

Traditional approach would use a database for everything. We don't:

```
Traditional:                    Pidgin:
┌────────────┐                 ┌────────────┐
│   Client   │                 │   Client   │
└─────┬──────┘                 └─────┬──────┘
      │                               │
      ▼                               ▼
┌────────────┐                 ┌────────────┐
│  Database  │                 │JSONL Files │
│ (blocking) │                 │(append-only)│
└────────────┘                 └─────┬──────┘
                                     │
                               ┌─────▼──────┐
                               │  DuckDB    │
                               │(post-import)│
                               └────────────┘
```

Benefits:
- **No write locks**: JSONL files are append-only
- **Standard tools**: Use `tail -f`, `grep`, `jq` during experiments
- **Zero data loss**: Even on crash, all events up to that point are saved
- **Batch analytics**: Import to DuckDB when convenient, not during runs

### File Structure

```
pidgin_output/
└── cosmic-prism_2024-07-16/         # Experiment directory
    ├── manifest.json                # Experiment metadata
    ├── events/
    │   └── events.jsonl             # Complete event stream
    ├── transcripts/
    │   └── conversation_0.md        # Human-readable output
    ├── state/
    │   └── metrics_0.json          # Computed metrics
    └── analysis/
        └── notebook.ipynb          # Auto-generated analysis
```

### State Management

Instead of a traditional database with complex state management:

1. **Events** are the source of truth (immutable, append-only)
2. **Manifest** provides efficient current state lookup
3. **Transcripts** offer human-readable views
4. **DuckDB** enables powerful post-hoc analysis

## Event-Driven Design

### Event Hierarchy

```
Event (base)
├── Conversation Events
│   ├── ConversationStartEvent
│   ├── ConversationEndEvent
│   └── ConversationCompleteEvent
├── Turn Events
│   ├── TurnStartEvent
│   └── TurnCompleteEvent
├── Message Events
│   ├── MessageRequestEvent
│   ├── MessageChunkEvent
│   └── MessageCompleteEvent
├── Analysis Events
│   ├── ConvergenceEvent
│   └── MetricsCalculatedEvent
└── System Events
    ├── APIErrorEvent
    ├── RateLimitEvent
    └── TokenUsageEvent
```

### Event Flow Example

Here's what happens during a single turn:

```
User Input: "Start conversation"
    │
    ▼
ConversationStartEvent
    │
    ▼
TurnStartEvent(turn=1)
    │
    ├─▶ MessageRequestEvent(agent=A)
    │       │
    │       ├─▶ MessageChunkEvent("The")
    │       ├─▶ MessageChunkEvent(" nature")
    │       ├─▶ MessageChunkEvent(" of...")
    │       │
    │       └─▶ MessageCompleteEvent(content="The nature of...")
    │
    ├─▶ MessageRequestEvent(agent=B)
    │       │
    │       └─▶ MessageCompleteEvent(content="Indeed, the...")
    │
    └─▶ TurnCompleteEvent(turn=1, convergence=0.23)
```

### Event Subscriptions

Components declare what events they care about:

```python
# Storage subscribes to message events
self.bus.subscribe(MessageCompleteEvent, self.store_message)

# Metrics calculator subscribes to turn completion
self.bus.subscribe(TurnCompleteEvent, self.calculate_metrics)

# UI subscribes to everything for live display
self.bus.subscribe(Event, self.update_display)
```

## Provider Architecture

### The Provider Interface

All providers implement this simple interface:

```python
class Provider(ABC):
    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens."""
        pass
```

### Provider Types

```
Provider (abstract)
├── API Providers
│   ├── AnthropicProvider    # Claude models
│   ├── OpenAIProvider       # GPT models
│   ├── GoogleProvider       # Gemini models
│   └── xAIProvider         # Grok models
└── Local Providers
    ├── TestProvider        # Deterministic testing
    └── OllamaProvider      # Local models via Ollama
```

### Message Transformation

Providers handle message transformation for their specific APIs:

```python
# What Pidgin sees (universal format)
Message(role="user", content="Hello", agent_id="agent_a")

# What Claude sees (Anthropic format)
{"role": "user", "content": "Hello"}

# What GPT sees (OpenAI format)  
{"role": "user", "content": "Hello"}
```

### Rate Limiting & Retries

Each provider manages its own rate limits:

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
┌──────▼──────┐
│Rate Limiter │ ◀── Provider-specific limits
└──────┬──────┘
       │
┌──────▼──────┐
│   Retries   │ ◀── Exponential backoff
└──────┬──────┘
       │
┌──────▼──────┐
│     API     │
└─────────────┘
```

## Experiment System

### Architecture for Scale

While a single conversation is simple, experiments can run hundreds:

```
Experiment Definition (YAML)
           │
    ┌──────▼──────┐
    │  Experiment │
    │   Manager   │
    └──────┬──────┘
           │
    Splits into individual conversations
           │
    ┌──────┴──────┬──────────┬─────────┐
    ▼             ▼          ▼         ▼
Conversation  Conversation  ...   Conversation
    │             │                    │
    └─────────────┴────────────────────┘
                  │
           Sequential execution
           (respects rate limits)
```

### Daemon Architecture

Long-running experiments use Unix daemons:

```
1. User runs: pidgin experiment run spec.yaml --daemon
2. Main process forks daemon
3. Daemon writes PID to pidgin_output/experiments/active/
4. Daemon runs conversations sequentially
5. Monitor tracks progress via manifest.json
6. User can stop with: pidgin stop experiment-name
```

### Why Sequential?

The architecture supports parallel execution, but defaults to sequential because:

1. **Rate Limits**: Most APIs limit requests/minute
2. **Hardware**: Local models need GPU/CPU resources  
3. **Reliability**: Easier to debug and resume
4. **Research**: Reproducibility matters more than speed

Users can increase parallelism if their setup allows:
```yaml
parallel: 4  # Run 4 conversations simultaneously
```

## Metrics & Analysis

### Metrics Pipeline

```
Turn Completes
      │
      ▼
┌─────────────┐
│  Calculate  │
│  150+ Metrics│
└──────┬──────┘
       │
   Metrics include:
   • Vocabulary overlap
   • Message length trends  
   • Linguistic complexity
   • Topic consistency
   • Convergence patterns
       │
       ▼
┌─────────────┐
│Store in JSON│
│  and Event  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Import to  │
│   DuckDB    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Generate   │
│  Notebook   │
└─────────────┘
```

### Convergence Detection

The crown jewel of Pidgin's analysis:

```python
convergence = weighted_average(
    vocabulary_overlap * 0.3,
    length_convergence * 0.2,
    style_similarity * 0.2,
    topic_consistency * 0.15,
    linguistic_patterns * 0.15
)
```

When convergence > threshold, conversations show:
- Repetitive vocabulary
- Similar message lengths
- Aligned linguistic style
- Consistent topics

## Extension Points

### Adding a Provider

1. Implement the Provider interface:
```python
class MyProvider(Provider):
    async def stream_response(self, messages, temperature):
        # Your implementation
        yield "response"
```

2. Register in `provider_builder.py`:
```python
if model.startswith("myprovider:"):
    return MyProvider(model)
```

### Adding Metrics

1. Add calculation in `MetricsCalculator`:
```python
def calculate_my_metric(self, messages):
    return {"my_metric": value}
```

2. Include in schema if persisting:
```python
# In schema.py
my_metric = Float()
```

### Adding Analysis

Subscribe to events and process:
```python
class MyAnalyzer:
    def __init__(self, bus):
        bus.subscribe(TurnCompleteEvent, self.analyze)
    
    def analyze(self, event):
        # Your analysis logic
```

## Design Decisions

### Why Event-Driven?

**Alternative considered**: Direct method calls between components

**Decision**: Event-driven architecture

**Rationale**:
- Complete decoupling enables easy testing
- Natural audit trail for research
- Simple to extend without modifying core
- Async events prevent blocking

### Why JSONL Instead of Database-First?

**Alternative considered**: SQLite/PostgreSQL for everything

**Decision**: JSONL files with DuckDB for analysis

**Rationale**:
- No write contention during experiments
- Standard Unix tools for debugging
- Append-only is crash-safe
- DuckDB better for analytical queries

### Why Streaming Responses?

**Alternative considered**: Wait for complete responses

**Decision**: Stream tokens as they arrive

**Rationale**:
- Better user experience (see progress)
- Enables real-time monitoring
- Allows early experiment termination
- Matches how humans converse

### Why Abstract Providers?

**Alternative considered**: Direct API integration

**Decision**: Provider interface abstraction

**Rationale**:
- Mix different models freely
- Easy testing with deterministic providers
- Future-proof for new APIs
- Clean separation of concerns

## Performance Characteristics

### Scalability
- **Vertical**: Limited by API rate limits, not architecture
- **Horizontal**: Can run multiple experiments on different machines
- **Storage**: O(n) with conversation length, optimized for write

### Latency
- **Message generation**: Dominated by API latency (~1-5s)
- **Event processing**: Microseconds per event
- **Storage writes**: Async, doesn't block conversation

### Resource Usage
- **Memory**: O(1) - only recent messages in memory
- **CPU**: Minimal, mostly waiting for I/O
- **Disk**: ~1KB per message, compressed well

## Security Considerations

- **API Keys**: Never logged, only in environment
- **File Access**: Respects OS permissions
- **Network**: Only connects to configured endpoints
- **Local Models**: Run in Ollama's sandboxed environment

## Future Architecture Considerations

The architecture is designed to accommodate:
- **Multi-modal models**: Events can carry any content type
- **Group conversations**: Event system handles n participants
- **Real-time analysis**: Stream processing of metrics
- **Distributed experiments**: Event bus could be networked

---

This architecture enables Pidgin to be a powerful research tool while remaining simple to use and extend. The event-driven design provides complete observability of AI conversations while maintaining clean separation between components.