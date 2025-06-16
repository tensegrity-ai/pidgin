# Pidgin Architecture

## Overview

Event-driven system for recording AI-to-AI conversations. Built to support n-agent conversations in the future, currently implements 2-agent only.

## Core Architecture

### Event System

Central event bus enables:
- Complete conversation recording
- Future n-agent support
- Pause/resume functionality
- Comprehensive logging to `events.jsonl`

### Main Components

#### Conductor (`conductor.py`)
- Orchestrates conversations through events
- Handles Ctrl+C interrupts
- Manages turn flow
- ~500 lines after refactoring

#### Providers (`providers/`)
- Clean abstraction for AI APIs
- All providers support streaming
- Event-aware wrappers emit events during streaming
- Supports: Anthropic, OpenAI, Google, xAI

#### UserInteractionHandler (`user_interaction.py`)
- Handles pause/resume menus
- Manages timeout decisions
- Future home for message injection

#### Output Management
- `OutputManager` - Creates directory structure
- `TranscriptManager` - Saves conversation files
- All output goes to `./pidgin_output/`

### Event Types

Currently implemented events:
- `ConversationStartEvent/EndEvent`
- `TurnStartEvent/CompleteEvent`
- `MessageRequestEvent/CompleteEvent`
- `MessageChunkEvent` (streaming)
- `InterruptRequestEvent`
- `ConversationPausedEvent/ResumedEvent`
- `ErrorEvent/APIErrorEvent/ProviderTimeoutEvent`

## Experimental Features (Unvalidated)

### Convergence Metrics (`convergence.py`)
- Measures vocabulary overlap and compression patterns
- **Not scientifically validated**
- Needs rigorous testing to determine if meaningful
- Currently just logs metrics without analysis

### Context Tracking (`context_manager.py`)
- Token counting for context window management
- Not yet integrated with conversation flow
- Placeholder for future context-aware features

## Not Yet Implemented

### Critical for Research
- **Batch Experiments** - Need to run hundreds of conversations
- **Statistical Analysis** - Validate if patterns are real
- **Control Conditions** - Test against random baselines
- **Message Injection** - Modify conversations mid-stream

### Future Capabilities
- **Checkpoint/Resume** - Event replay from specific points
- **N-agent Support** - Architecture ready, needs implementation
- **Real-time Analysis** - Pattern detection during conversations

## Data Flow

1. User starts conversation via CLI
2. Conductor orchestrates via events
3. Providers stream responses as events
4. All events logged to `events.jsonl`
5. Transcripts saved after conversation
6. Ctrl+C can interrupt at any time

## Architecture Decisions

### Why Event-Driven?
- Enables future n-agent conversations
- Complete audit trail for research
- Supports pause/resume functionality
- Allows replay and analysis

### Current Limitations
- Single-threaded (batch experiments need parallel execution)
- 2-agent only (n-agent requires conductor refactor)
- No real-time analysis (events logged but not processed)

## Next Steps for Valid Research

1. **Batch Infrastructure** - Run many conversations with identical conditions
2. **Statistical Tools** - Analyze patterns across conversations
3. **Control Design** - Test against shuffled/random baselines
4. **Hypothesis Testing** - Pre-register experiments
5. **Reproducibility** - Version lock, seed management

## Technical Status

- **Stable**: Event system, provider abstraction, basic flow
- **Experimental**: Convergence metrics, pattern detection
- **Missing**: Batch runner, analysis pipeline, validation tools