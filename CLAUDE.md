# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_dialogue.py

# Run tests with verbose output and coverage report
pytest -v --cov=pidgin --cov-report=html --cov-report=term

# Run tests matching a pattern
pytest -k "test_conductor"
```

### Code Quality
```bash
# Format code (automatically fixes formatting)
black pidgin tests

# Sort imports
isort pidgin tests

# Lint code (checks for style issues)
flake8 pidgin tests

# Type checking
mypy pidgin
```

### Development Setup

#### Virtual Environment Setup (Recommended)
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

#### Alternative Installation Methods
```bash
# Using Poetry (if you have poetry installed)
poetry install

# Using pipx for global installation
pipx install -e .

# Direct pip install (requires --break-system-packages on some systems)
pip install -e ".[dev]" --break-system-packages
```

#### Post-Installation Setup
```bash
# Install pre-commit hooks for automatic formatting
pre-commit install
```

## High-Level Architecture

### Core System Flow
1. **DialogueEngine** orchestrates conversations between two AI agents
2. **Router** manages message flow between agents using their providers
3. **Conductor** (should be InterventionHandler) intercepts messages for human control
4. **Managers** handle specific concerns:
   - **AttractorManager**: Detects repetitive patterns (hypothesis to validate)
   - **CheckpointManager**: Enables pause/resume
   - **ContextManager**: Prevents context window overflows
   - **ConvergenceCalculator**: Tracks when agents sound alike
   - **TranscriptManager**: Saves conversations in JSON/Markdown

### Key Patterns

**Manager Pattern**: Specialized managers handle distinct responsibilities (checkpoint, context, attractors). Each manager is optional and the system gracefully continues if one fails.

**Provider Abstraction**: All AI providers (Anthropic, OpenAI, Google, xAI) implement a simple interface with `stream_response()`. This allows easy addition of new providers without changing core logic.

**Middleware Pattern**: Conductor modes act as message interceptors, allowing human intervention in AI conversations. Two modes exist:
- Manual: Pauses after each turn
- Flowing: Runs automatically until paused

**Turn Model (2+1 Tuple)**: A turn consists of agent_a message, agent_b message, and optional intervention. This is the atomic unit of conversation.

### Important Implementation Details

**Message Flow**: Messages alternate between agents with full conversation history provided to each. The router converts history to the appropriate format for each provider's API.

**Checkpoint System**: Full conversation state is atomically saved to disk, including messages, metrics, and manager states. Checkpoints occur automatically every 10 turns or on pause.

**Context Management**: Each model has known context limits (e.g., Claude: 200k tokens). The system warns at 80% capacity and auto-pauses at 95% to prevent crashes.

**Convergence Detection**: Measures structural similarity between agent responses. This is the only validated "attractor" metric currently.

**Intervention System**: In flowing mode, Ctrl+C pauses for intervention. In manual mode, the system asks after each turn.

### Working with Transcripts

Transcripts are saved to `~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/`:
- `conversation.json`: Full data including metrics
- `conversation.md`: Human-readable format
- `conversation.checkpoint`: Resumable state
- `attractor_analysis.json`: Pattern detection results (experimental)

The JSON format includes the conversation with metrics for convergence tracking, turn analysis, and conductor interventions.

### Testing Approach

Tests use pytest with async support. Key test files:
- `test_dialogue.py`: Core conversation flow
- `test_conductor.py`: Message interception
- `test_attractors.py`: Pattern detection (experimental)
- `test_checkpoint.py`: Pause/resume functionality
- `test_context_management.py`: Context limit handling

When adding features, write tests that verify both the happy path and edge cases, especially around pause/resume functionality.

## Imminent Event Architecture

The codebase is about to undergo a major transformation to event-driven architecture:

1. **EventBus**: Central nervous system for all communication
2. **Turn-based Events**: `TurnStartEvent`, `TurnCompleteEvent` with 2+1 tuple
3. **Streaming Events**: `MessageChunkEvent` for real-time updates
4. **Decoupled Components**: Everything communicates via events

This will enable:
- Parallel experiment execution
- Perfect observability
- Natural streaming UI updates
- Clean component boundaries

## Current Cleanup Priorities

Before implementing events, remove:
1. Message `source` field and `MessageSource` enum
2. Legacy `route_message()` method
3. Fake streaming interrupt handling
4. Human/mediator/system message type complexity

## Commit Message Style

Use lowercase commit messages for consistency, unless referring to specific code or proper nouns:

```bash
# Good examples:
git commit -m "add event bus implementation"
git commit -m "fix context window calculation in ContextManager"
git commit -m "implement turn-based event system"

# Avoid:
git commit -m "Add Event Bus Implementation"
git commit -m "Fix Context Window Calculation"
```

This maintains a clean, consistent git history while preserving readability.