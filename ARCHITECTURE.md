# Pidgin Architecture Documentation

## Overview

Pidgin is an event-driven conversation research tool. This document describes what's actually implemented.

## Core Architecture (Working ✅)

### Event-Driven System

Everything flows through events:
- `EventBus` - Central publish/subscribe system
- `events.jsonl` - Complete record of all events
- Full observability of all actions

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

## Partially Implemented (🚧)

### Convergence Detection (`convergence.py`)
- `ConvergenceCalculator` exists and calculates metrics
- Measures structural similarity between responses
- **NOT SHOWN IN UI**
- **NO AUTO-PAUSE** despite what old docs claim
- Metrics are calculated but not used

### Context Management (`context_manager.py`)
- Token counting methods exist
- Model context limits defined
- **NOT INTEGRATED** into conversation flow
- **NO WARNINGS DISPLAYED**
- Would need to be wired into conductor

## Not Implemented (❌)

### Checkpoint System
- Completely removed in favor of event-driven approach
- Event logs are the only state
- No resume from checkpoint functionality

### Message Injection
- Can pause but can't inject messages
- Framework exists in `UserInteractionHandler`
- Need to implement intervention flow

### Attractor Detection
- Experimental framework exists
- Not validated or actively used
- Needs research to determine if meaningful

## Data Flow

1. User starts conversation via CLI
2. Conductor orchestrates via events
3. Providers stream responses as events
4. All events logged to `events.jsonl`
5. Transcripts saved after conversation
6. Ctrl+C can interrupt at any time

## Future Architecture

### Planned Event Replay
- Replay `events.jsonl` to reconstruct state
- Enable branching conversations
- Time-travel debugging

### Batch Execution
- Run multiple conversations in parallel
- Aggregate event streams
- Live monitoring dashboard

## Technical Debt

1. Convergence metrics calculated but not used
2. Context management not integrated
3. Some provider retry logic could be unified
4. Event serialization could be more efficient