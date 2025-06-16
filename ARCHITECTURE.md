# Architecture

This document describes the actual implementation - a well-structured research tool with ~20 modules, not a minimal prototype.

## Overview

Pidgin uses an event-driven architecture where every action emits an event. These events are both the communication mechanism and the permanent record.

```
User → CLI → Conductor → EventBus → Components
                ↓           ↓
            Providers    events.jsonl
```

## Core Components

### EventBus (`event_bus.py`)
- Central publish/subscribe system
- Writes all events to JSONL in real-time
- No hidden state - if it's not in an event, it didn't happen

### Conductor (`conductor.py`)
- Orchestrates conversations through events
- Handles interrupt signals (Ctrl+C)
- ~500 lines, manageable complexity

### Event Types (`events.py`)
- `ConversationStartEvent` / `ConversationEndEvent`
- `MessageRequestEvent` / `MessageCompleteEvent`
- `TurnStartEvent` / `TurnCompleteEvent`
- Various error and control events

### Providers (`providers/`)
- Wrapped to emit events during streaming
- Support for Anthropic, OpenAI, Google, xAI
- Consistent interface despite API differences

## How a Conversation Flows

1. **Setup**: CLI creates Conductor with providers
2. **Initialize**: EventBus created, output directory prepared
3. **Start**: System prompts sent (if any), initial prompt displayed
4. **Turns**: For each turn:
   - Request message from Agent A
   - Stream response, emitting chunk events
   - Request message from Agent B
   - Stream response, emitting chunk events
   - Emit turn complete event
5. **End**: Save transcripts, close event log

## Data Flow

All conversation data flows through events:
```
MessageRequestEvent → Provider → MessageChunkEvents → MessageCompleteEvent
```

Every event is logged to `./pidgin_output/conversations/*/events.jsonl`

## Current Limitations

### Single Conversation Only
- No parallel execution
- No batch runner
- One conversation at a time

### Basic Analysis
- Convergence metrics calculated but not displayed
- No statistical tools
- No pattern detection beyond simple structural matching

### Limited Intervention
- Can pause (Ctrl+C) but can't inject messages
- No dynamic prompt modification
- No mid-conversation adjustments

## Design Decisions

### Why Events?
- Complete observability
- Natural fit for streaming
- Enables future features (replay, analysis)
- No hidden state to debug

### Why Not Checkpoints?
- Events contain full history
- Checkpoints were redundant
- Simpler is better

### Current 2-Agent Focus
- Architecture could support n-agents
- Current implementation is 2-agent only
- No immediate plans for multi-agent features

## File Structure

```
pidgin/
├── conductor.py          # Main orchestrator (~500 lines)
├── event_bus.py         # Event publish/subscribe system
├── events.py            # Event type definitions
├── event_logger.py      # Event display formatting
├── display_filter.py    # Human-readable output filtering
│
├── providers/           # AI provider integrations
│   ├── base.py         # Provider interface
│   ├── anthropic.py    # Claude models
│   ├── openai.py       # GPT/O-series models
│   ├── google.py       # Gemini models
│   ├── xai.py          # Grok models
│   └── event_wrapper.py # Event-aware provider wrapper
│
├── dialogue_components/ # Separated UI/display components
│   ├── display_manager.py
│   ├── metrics_tracker.py
│   ├── progress_tracker.py
│   └── response_handler.py
│
### Pattern Detection

The system uses a **convergence threshold** approach:
- Calculates structural similarity between agents (0.0-1.0)
- Monitors vocabulary overlap, message length ratios, syntactic patterns
- Stops conversation when convergence exceeds configured threshold
- No prescriptive pattern categories - just measures similarity

The system uses a simple convergence threshold approach - when agents become too similar (configurable, default 0.85), the conversation stops automatically.
│
├── cli.py              # Command-line interface
├── config.py           # Configuration management
├── context_manager.py  # Token/context window tracking
├── convergence.py      # Convergence metrics calculator
├── dimensional_prompts.py # Prompt generation system
├── intervention_handler.py # Pause/resume handling (was conductor.py)
├── logger.py           # Logging configuration
├── metrics.py          # Turn metrics calculation
├── models.py           # Model configurations and metadata
├── output_manager.py   # Output directory management
├── router.py           # Message routing between agents
├── system_prompts.py   # System prompt templates
├── transcripts.py      # Transcript generation
├── types.py            # Type definitions
└── user_interaction.py # User interaction handling
```

## Output Structure

Each conversation creates:
```
./pidgin_output/
└── conversations/
    └── YYYY-MM-DD/
        └── HHMMSS_xxxxx/
            ├── events.jsonl    # Complete event log
            ├── conversation.json # Structured data
            └── conversation.md   # Human-readable
```

## What's Not Built

- **Batch execution**: Critical for research validity
- **Event replay**: Can't resume from logs yet
- **Analysis pipeline**: No tools to find patterns
- **Message injection**: Framework exists but not connected
- **Real token counting**: Just word estimates

## Future Possibilities

The event architecture enables:
- Replay from any point
- Time-travel debugging
- Statistical analysis
- Pattern detection
- Multi-agent support

But these aren't built yet. We focused on getting clean data capture working first.

---

This architecture is complete for its current purpose: recording single conversations with full observability. The next critical need is batch execution for statistical validity.