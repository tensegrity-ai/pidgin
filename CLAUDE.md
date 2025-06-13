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

## High-Level Architecture

### Core System Flow
1. **DialogueEngine** orchestrates conversations between two AI agents
2. **Router** manages message flow between agents using their providers
3. **Conductor** (optional) intercepts messages for human control
4. **Managers** handle specific concerns:
   - **AttractorManager**: Detects repetitive patterns
   - **CheckpointManager**: Enables pause/resume
   - **ContextManager**: Prevents context window overflows
   - **ConvergenceCalculator**: Tracks when agents sound alike
   - **TranscriptManager**: Saves conversations in JSON/Markdown

### Key Patterns

**Manager Pattern**: Specialized managers handle distinct responsibilities (checkpoint, context, attractors). Each manager is optional and the system gracefully continues if one fails.

**Provider Abstraction**: All AI providers (Anthropic, OpenAI, Google, xAI) implement streaming interfaces with `get_next_response_stream()`. This allows real-time response display with clean Rich status spinners and easy addition of new providers without changing core logic.

**Middleware Pattern**: Conductor modes act as message interceptors, allowing human intervention in AI conversations. Two modes exist:
- Manual: Pauses before each message for approval
- Flowing: Runs automatically until paused with Ctrl+C

**Configuration Hierarchy**: Settings flow from defaults → config files → runtime flags. Config files are loaded from standard locations (~/.config/pidgin/pidgin.yaml, ~/.config/pidgin.yaml, ~/.pidgin.yaml, ./pidgin.yaml) using dot notation access.

### Important Implementation Details

**Message Flow**: Messages alternate between agents with full conversation history provided to each. The router converts history to the appropriate format for each provider's API.

**Checkpoint System**: Full conversation state is atomically saved to disk, including messages, metrics, and manager states. Checkpoints occur automatically every 10 turns or on pause.

**Context Management**: Each model has known context limits (e.g., Claude: 200k tokens). The system warns at 80% capacity and auto-pauses at 95% to prevent crashes.

**Attractor Detection**: Only structural pattern detection is implemented (not semantic). Checks occur every 5 turns by default and can trigger pause or stop actions.

**Streaming Display**: All AI responses use Rich status spinners (e.g., "Agent A is responding...") for clean, non-conflicting terminal output. No complex keyboard detection during streaming - interrupts happen at turn boundaries.

**Pause and Control**: Press Ctrl+C anytime to pause conversation. The conductor activates at the next turn boundary, allowing message injection as different personas (Human, System, Mediator). The conversation resumes after intervention.

### Working with Transcripts

Transcripts are saved to `~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/`:
- `conversation.json`: Full data including metrics
- `conversation.md`: Human-readable format
- `conversation.checkpoint`: Resumable state
- `attractor_analysis.json`: Pattern detection results

The JSON format includes the conversation with optional metrics for convergence tracking, turn analysis, and conductor interventions.

### Testing Approach

Tests use pytest with async support. Key test files:
- `test_dialogue.py`: Core conversation flow
- `test_conductor.py`: Message interception
- `test_attractors.py`: Pattern detection
- `test_checkpoint.py`: Pause/resume functionality
- `test_context_management.py`: Context limit handling

When adding features, write tests that verify both the happy path and edge cases, especially around pause/resume functionality.

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