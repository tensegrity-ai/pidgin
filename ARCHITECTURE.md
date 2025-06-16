# Pidgin Architecture Documentation

## Overview

Pidgin is a conversation runner that logs everything to JSONL files. This document describes what actually exists in the codebase (not what was originally envisioned).

## What Actually Works

### Event System (Over-engineered but functional)

The entire system publishes events to a central bus:
- `EventBus` - A pub/sub system (overkill for this use case)
- `events.jsonl` - Logs every tiny action as JSON
- Generates massive log files for simple conversations

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

## Code That Exists But Does Nothing

### Convergence Detection (`convergence.py`)
- Calculates arbitrary "similarity" metrics
- Has no scientific basis or validation
- Metrics are computed but never used
- Original vision was to detect "convergent communication"
- In reality, just measures text similarity with made-up formulas

### Context Management (`context_manager.py`)
- Token counting code that isn't connected to anything
- Would theoretically warn about context limits
- Never actually called during conversations
- Another remnant of the original ambitious vision

## Things That Don't Work

### Checkpoint/Resume
- Can't resume previous conversations
- Event logs exist but replay isn't implemented
- The "event-driven" design was supposed to enable this

### Message Injection
- You can pause but can't add your own messages
- The UI shows a pause menu but that's it

### "Attractor Detection"
- Pseudoscientific concept from the original vision
- Some experimental code exists
- No evidence these "attractors" are real phenomena
- Likely just seeing patterns in randomness

## Data Flow

1. User starts conversation via CLI
2. Conductor orchestrates via events
3. Providers stream responses as events
4. All events logged to `events.jsonl`
5. Transcripts saved after conversation
6. Ctrl+C can interrupt at any time

## Unrealistic Future Plans

These were planned but are unlikely to happen:
- Event replay (would require significant refactoring)
- Batch execution (current design is single-threaded)
- Live dashboard (would need complete UI rewrite)
- "Time-travel debugging" (buzzword with no clear meaning)

## Honest Assessment of Technical Debt

1. **Over-engineered for its actual purpose** - Event system is complex for a chat logger
2. **Half-implemented features everywhere** - Convergence, context, injection all partially done
3. **No scientific validation** - Metrics and patterns are arbitrary
4. **Original vision doesn't match reality** - Built for "emergence research" but just logs chats
5. **Event logs are huge** - Gigabytes of JSON for simple conversations
6. **Code complexity unjustified** - Could be 1/10th the size for same functionality