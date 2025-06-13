# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Run all tests with coverage
poetry run pytest

# Run specific test file
poetry run pytest tests/test_dialogue.py

# Run tests with verbose output and coverage report
poetry run pytest -v --cov=pidgin --cov-report=html --cov-report=term

# Run tests matching a pattern
poetry run pytest -k "test_conductor"
```

### Code Quality
```bash
# Format code (automatically fixes formatting)
poetry run black pidgin tests

# Sort imports
poetry run isort pidgin tests

# Lint code (checks for style issues)
poetry run flake8 pidgin tests

# Type checking
poetry run mypy pidgin
```

### Development Setup

#### Poetry Setup (Recommended)
This project uses Poetry for dependency management. Install Poetry first if you don't have it:

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install all dependencies and create virtual environment automatically
poetry install

# Run commands in the Poetry environment
poetry run pytest
poetry run pidgin --help
```

#### Alternative Installation Methods
```bash
# Using pipx for global installation
pipx install -e .

# Direct pip install (requires manual venv and --break-system-packages on some systems)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]" --break-system-packages
```

#### Post-Installation Setup
```bash
# Install pre-commit hooks for automatic formatting
pre-commit install
```

## High-Level Architecture (Current State - Pre-Event System)

### Core System Flow
1. **DialogueEngine** orchestrates conversations between two AI agents (⚠️ God object - 930+ lines)
2. **Router** manages message flow between agents using their providers (✅ Excellent design)
3. **Conductor** (optional) intercepts messages for human control (✅ Clean abstraction)
4. **Managers** handle specific concerns:
   - **AttractorManager**: Detects repetitive patterns (⚠️ Some test failures)
   - **CheckpointManager**: Enables pause/resume (✅ Robust)
   - **ContextManager**: Prevents context window overflows (⚠️ Type mismatches)
   - **ConvergenceCalculator**: Tracks when agents sound alike (✅ Functional)
   - **TranscriptManager**: Saves conversations in JSON/Markdown (✅ Clean)

### Key Patterns (Preserve in Rebuild)

**Router Protocol Pattern** ✅: Message routing with clean provider abstraction. Router interface provides excellent foundation for event-based system.

**Manager Pattern** ✅: Specialized managers handle distinct responsibilities. Each manager is optional and the system gracefully continues if one fails. Good model for event handlers.

**Provider Abstraction** ✅: All AI providers implement streaming interfaces with `get_next_response_stream()`. Clean abstraction allows easy addition of new providers.

**Conductor Pattern** ✅: Message interceptor allowing human intervention. Two modes:
- Manual: Pauses before each message for approval  
- Flowing: Runs automatically until paused with Ctrl+C

**Rich UI Integration** ✅: Clean terminal display with status spinners and panels.

### Current Type Safety Status

**Type Checking**: ✅ 100% clean (0 mypy errors)
**Lint Status**: ✅ Only minor line length violations (42 issues, down from 131+)
**Import Organization**: ✅ Clean imports via isort
**Unused Code**: ✅ All unused variables removed

### Implementation Details & Current Issues

**Message Flow** ✅: Messages alternate between agents with full conversation history provided to each. The router converts history to the appropriate format for each provider's API.
- **Current State**: Clean transformation in `Router._build_agent_history`
- **Researcher Interventions**: Now working correctly with `[RESEARCHER NOTE]:` prefix

**Checkpoint System** ✅: Full conversation state is atomically saved to disk, including messages, metrics, and manager states. Checkpoints occur automatically every 10 turns or on pause.
- **Current State**: Robust serialization and resumption
- **Location**: `ConversationState` in `checkpoint.py`

**Context Management** ⚠️: Each model has known context limits (e.g., Claude: 200k tokens). The system warns at 80% capacity and auto-pauses at 95% to prevent crashes.
- **Current Issue**: Type mismatch - expects `Dict` but receives `Message` objects
- **Location**: `ContextWindowManager.get_remaining_capacity()` 
- **Workaround**: Manual conversion to dict format in multiple places

**Attractor Detection** ⚠️: Only structural pattern detection is implemented (not semantic). Checks occur every 5 turns by default and can trigger pause or stop actions.
- **Current Issue**: Some tests failing in `test_attractors.py`
- **Recommendation**: Consider making optional in rebuild

**Streaming Display** ✅: All AI responses use Rich status spinners (e.g., "Agent A is responding...") for clean, non-conflicting terminal output. No complex keyboard detection during streaming - interrupts happen at turn boundaries.
- **Current State**: Clean implementation with proper error handling
- **One Minor Issue**: Type ignore comment needed for async iterator

**Pause and Control** ✅: Press Ctrl+C anytime to pause conversation. The conductor activates at the next turn boundary, allowing researcher interventions.
- **Current State**: Simplified to just "researcher" interventions (no more human/system/mediator confusion)
- **UI**: Clean Rich-based intervention interface

### Working with Transcripts

Transcripts are saved to `~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/`:
- `conversation.json`: Full data including metrics
- `conversation.md`: Human-readable format
- `conversation.checkpoint`: Resumable state
- `attractor_analysis.json`: Pattern detection results

The JSON format includes the conversation with optional metrics for convergence tracking, turn analysis, and conductor interventions.

### Testing Status & Guidelines

Tests use pytest with async support. Current coverage and status:

**✅ Well-Tested Modules**:
- `test_conductor.py`: Message interception (17/17 passing)
- `test_checkpoint.py`: Pause/resume functionality (7/7 passing)  
- `test_context_management.py`: Context limit handling (12/12 passing)

**⚠️ Modules Needing Attention**:
- `test_attractors.py`: Pattern detection (some failures in party attractor tests)
- Integration tests missing for full conversation flows

**Testing Guidelines for Rebuild**:
1. **Message Flow Tests**: Verify message transformations at each step
2. **Event Handler Tests**: Test each manager as an event handler
3. **UI Tests**: Mock Rich console for terminal display testing  
4. **Error Handling Tests**: Test provider failures, rate limits, interruptions
5. **State Tests**: Verify event sourcing and state reconstruction

**Current Test Infrastructure**:
- Async test support with pytest-asyncio
- Good mocking patterns for providers
- Clean fixtures for conversation setup

## Current Control System

### Streaming and Interrupts
- **Clean Display**: Uses Rich `console.status()` with spinners for non-conflicting output
- **Simple Interrupts**: Ctrl+C sets conductor pause state, triggers at turn boundaries
- **No Terminal Mode Conflicts**: No raw terminal mode or complex keyboard detection
- **Cross-Platform**: Works consistently on Windows, macOS, and Linux

### Turn Display
- **Every Turn**: Simple "Turn X/Y" counter
- **Every 5 Turns**: Detailed status with convergence, context usage, and controls
- **Smart Context Display**: Only shows context % when >50% to reduce noise

### Pause and Resume Flow
1. User presses **Ctrl+C** anytime during conversation
2. System shows "Paused. Intervention available at next turn."
3. Current agent response completes cleanly
4. Conductor intervention UI appears at turn boundary
5. User can inject messages or continue conversation
6. Normal flow resumes after intervention

This approach prioritizes simplicity and reliability over complex real-time interruption.

## Commit Message Style

Use lowercase commit messages for consistency, unless referring to specific code or proper nouns:

```bash
# Good examples:
git commit -m "add OpenAI provider support"
git commit -m "fix context window calculation in ContextManager"
git commit -m "implement structural attractor detection system"

# Avoid:
git commit -m "Add OpenAI Provider Support"
git commit -m "Fix Context Window Calculation"
```

This maintains a clean, consistent git history while preserving readability.

---

## Architectural Notes for Event System Rebuild

### What to Preserve ✅
1. **Router Protocol Pattern**: Excellent foundation for event routing
2. **Provider Abstraction**: Clean, extensible interface
3. **Manager Pattern**: Good model for event handlers  
4. **Rich UI Integration**: Terminal display works well
5. **Checkpoint System**: Robust state management
6. **Type Safety**: Comprehensive type annotations

### What to Refactor ⚠️
1. **DialogueEngine**: Break up god object (930+ lines)
2. **Context Manager**: Fix type mismatches (Dict vs Message)
3. **Message Attribution**: Simplify to agents + researcher only
4. **State Management**: Centralize in event store

### Critical Issues to Address 🚨
1. **Type ignore comment** in dialogue.py:954 (async iterator)
2. **Attractor test failures** in pattern detection
3. **Context type mismatches** throughout system
4. **Tight coupling** between DialogueEngine and all managers

### Event System Migration Strategy
1. **Phase 1**: Extract event bus using Router pattern
2. **Phase 2**: Convert managers to event handlers  
3. **Phase 3**: Implement event sourcing for state
4. **Phase 4**: Replace DialogueEngine with orchestrator

### Key Files for Rebuild Team
- `router.py` - Excellent pattern to follow ✅
- `providers/base.py` - Clean abstraction ✅  
- `conductor.py` - Good event handler model ✅
- `dialogue.py` - Anti-pattern (god object) ❌
- `types.py` - Solid foundation ✅