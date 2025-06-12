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
3. **Conductor** (optional) intercepts messages for human control
4. **Managers** handle specific concerns:
   - **AttractorManager**: Detects repetitive patterns
   - **CheckpointManager**: Enables pause/resume
   - **ContextManager**: Prevents context window overflows
   - **ConvergenceCalculator**: Tracks when agents sound alike
   - **TranscriptManager**: Saves conversations in JSON/Markdown

### Key Patterns

**Manager Pattern**: Specialized managers handle distinct responsibilities (checkpoint, context, attractors). Each manager is optional and the system gracefully continues if one fails.

**Provider Abstraction**: All AI providers (Anthropic, OpenAI) implement a simple interface with `get_response()`. This allows easy addition of new providers without changing core logic.

**Middleware Pattern**: Conductor modes act as message interceptors, allowing human intervention in AI conversations. Two modes exist:
- Manual: Pauses before each message
- Flowing: Runs automatically until paused

**Configuration Hierarchy**: Settings flow from defaults → config files → runtime flags. Config files are loaded from standard locations (~/.config/pidgin/pidgin.yaml, ~/.config/pidgin.yaml, ~/.pidgin.yaml, ./pidgin.yaml) using dot notation access.

### Important Implementation Details

**Message Flow**: Messages alternate between agents with full conversation history provided to each. The router converts history to the appropriate format for each provider's API.

**Checkpoint System**: Full conversation state is atomically saved to disk, including messages, metrics, and manager states. Checkpoints occur automatically every 10 turns or on pause.

**Context Management**: Each model has known context limits (e.g., Claude: 200k tokens). The system warns at 80% capacity and auto-pauses at 95% to prevent crashes.

**Attractor Detection**: Only structural pattern detection is implemented (not semantic). Checks occur every 5 turns by default and can trigger pause or stop actions.

**External Message Injection**: In conductor mode, users can inject messages as different personas (External, Agent A, Agent B). External messages auto-resume the conversation flow.

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