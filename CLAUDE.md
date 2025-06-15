# Development Guide for Pidgin

## Current State (Accurate as of December 2024)

### ✅ What's Working
- Event-driven architecture with EventBus
- Streaming from all providers  
- Ctrl+C interrupt system
- Clean component separation
- Output to `./pidgin_output/`
- Dimensional prompt system
- Full conversation transcripts

### 🚧 What's Partial
- Convergence calculation (not displayed)
- Context tracking (not integrated)
- Message injection framework (not connected)

### ❌ What's Not Done
- Checkpoint/resume system (removed)
- Batch experiments
- Live dashboard
- Pattern analysis
- Event replay

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

## Architecture Overview

The system is event-driven:
- `Conductor` orchestrates via events
- `EventBus` handles all communication
- `events.jsonl` is the source of truth
- No checkpoint files

### Key Files

- `conductor.py` - Main orchestrator (~500 lines)
- `event_bus.py` - Event system core
- `events.py` - Event type definitions
- `user_interaction.py` - User interaction handling
- `providers/` - AI provider integrations
- `display_filter.py` - UI display logic

### Data Flow

1. User starts conversation via CLI
2. Conductor creates output directory
3. Events flow through EventBus
4. Providers stream responses
5. All events logged to events.jsonl
6. Ctrl+C interrupts handled gracefully
7. Transcripts saved on completion

## Development Workflow

```bash
# Run a test conversation
pidgin chat -a claude -b gpt -t 10

# See all events (verbose mode)
pidgin chat -a claude -b gpt -t 10 -v

# Check output
ls ./pidgin_output/conversations/*/
```

## Adding Features

New features should:
1. Emit events for all actions
2. Work with existing event flow
3. Not create hidden state
4. Be observable through events

## Testing

```bash
# Run tests
pytest

# Test specific component
pytest tests/test_conductor.py
```

## Common Issues

1. **Output location**: Always `./pidgin_output/`, not home directory
2. **No checkpoints**: Events are the only state
3. **Convergence metrics**: Calculated but not shown (yet)
4. **Resume command**: Shows "coming soon" message

## Commit Message Style

Use lowercase commit messages for consistency:

```bash
# Good examples:
git commit -m "add event bus implementation"
git commit -m "fix context window calculation"
git commit -m "implement turn-based event system"

# Avoid:
git commit -m "Add Event Bus Implementation"
git commit -m "Fix Context Window Calculation"
```

This maintains a clean, consistent git history.