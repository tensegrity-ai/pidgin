# Pidgin Architecture

## Overview

Pidgin is an event-driven system for recording and analyzing AI-to-AI conversations. Every action emits an event, creating complete observability of conversation dynamics.

```
User → CLI → Conductor → EventBus → Components
                ↓           ↓
            Providers   events.jsonl
                ↓           ↓
            AI APIs    SQLite DB
```

## Core Components

### EventBus (`core/event_bus.py`)
Central nervous system. All components communicate through events:
- Publishers emit events (no direct coupling)
- Subscribers react to events they care about
- Every event is logged to `events.jsonl`
- Complete replay capability (future feature)

### Conductor (`core/conductor.py`)
Orchestrates conversations:
- Manages conversation flow
- Handles interrupts (Ctrl+C)
- Emits events for every action
- No business logic - just coordination

### Providers (`providers/`)
Abstractions over AI APIs:
- `anthropic.py` - Claude models
- `openai.py` - GPT and O-series models
- `google.py` - Gemini models
- `xai.py` - Grok models

Each wrapped with `EventAwareProvider` for automatic event emission.

### Experiment System (`experiments/`)
Batch execution and analysis:
- `ExperimentRunner` - Manages parallel conversations
- `MetricsCalculator` - Computes ~150 linguistic metrics
- `Database` - SQLite storage for metrics
- `Dashboard` - Real-time visualization

## Event Flow Example

```
1. User runs: pidgin chat -a claude -b gpt
2. CLI creates Conductor with providers
3. Conductor emits ConversationStartEvent
4. Conductor requests message from Agent A
   → MessageRequestEvent
5. Provider streams response
   → MessageChunkEvent (multiple)
   → MessageCompleteEvent
6. Metrics calculated
   → MetricsCalculatedEvent
7. Turn completes
   → TurnCompleteEvent (includes convergence)
8. Repeat for Agent B
9. Eventually ConversationEndEvent
```

## Data Flow

### Single Conversation
```
Conversation
    ↓
events.jsonl (every event)
    ↓
conversation.json (final state)
conversation.md (human readable)
```

### Batch Experiments
```
100x Conversations
    ↓
SQLite Database
    ├── experiments table
    ├── conversations table
    ├── turns table (~150 metrics)
    └── word_frequencies table
    ↓
Dashboard (real-time view)
Analysis Tools
```

## Key Design Principles

### 1. Everything Is An Event
No hidden state. If something happens, it emits an event. This enables:
- Complete observability
- Replay capability
- Loose coupling
- Easy testing

### 2. Streams Over Batches
Responses stream token by token:
- Real-time display
- Interrupt capability
- Natural conversation flow

### 3. Metrics Not Judgments
We calculate objective metrics:
- Type-token ratio
- Vocabulary overlap
- Shannon entropy
- Message lengths

We don't interpret what they mean.

## File Organization

```
pidgin/
├── core/              # Event system, conductor, types
├── providers/         # AI provider integrations
├── experiments/       # Batch execution system
├── analysis/          # Metrics and convergence
├── ui/                # Display and interaction
├── config/            # Models, prompts, settings
└── io/                # File I/O, transcripts

./pidgin_output/       # All output goes here
├── conversations/     # Individual conversations
└── experiments/       # Batch experiment data
    └── experiments.db # Metrics database
```

## Extensibility Points

### Adding a Provider
1. Implement `Provider` interface
2. Add to provider registry
3. Automatic event support via wrapper

### Adding a Metric
1. Add to `MetricsCalculator`
2. Add database column
3. Add to dashboard display

### Adding Event Types
1. Define event in `events.py`
2. Emit from relevant component
3. Subscribe where needed

## Performance Characteristics

- **Startup**: <1 second
- **Streaming latency**: <100ms
- **Metric calculation**: <50ms per turn
- **Dashboard refresh**: 4Hz (250ms)
- **Parallel conversations**: 10+ (rate limit dependent)

## What Makes This Architecture Interesting

1. **Complete Record**: Every conversation is perfectly recorded via events
2. **No Hidden State**: Everything observable through event stream
3. **Natural Parallelism**: Event-driven = easy concurrent execution
4. **Scientific Reproducibility**: Same inputs → same outputs
5. **Live Analysis**: Watch patterns emerge in real-time

The architecture is built for research - we're not trying to coordinate AI agents or build protocols. We're trying to understand what happens when they talk.