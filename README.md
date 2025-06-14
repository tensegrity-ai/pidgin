# Pidgin

AI conversation research tool for studying emergent communication between language models.

## Overview

Pidgin enables conversations between AI agents to study how they develop communication patterns and linguistic convergence. It features automatic detection of conversation dynamics, pause/resume functionality, and comprehensive model support across multiple providers.

## Installation

### Prerequisites

- Python 3.9 or higher
- API keys for the providers you want to use:
  - Anthropic API key (for Claude models)
  - OpenAI API key (for GPT models)
  - Google API key (for Gemini models)
  - xAI API key (for Grok models)

### Install from source

```bash
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin
pip install -e .
```

## Configuration

Set your API keys as environment variables:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."
```

## Quick Start

### Basic Conversations

```bash
# Basic conversation (10 turns)
pidgin chat -a claude -b gpt -t 10

# Custom initial prompt
pidgin chat -a opus -b gpt-4.1 -t 20 -p "Let's discuss compression algorithms"

# Manual mode for turn-by-turn control
pidgin chat -a claude -b gemini -t 20 --manual

# Disable experimental features
pidgin chat -a haiku -b nano -t 100 --no-attractor-detection
```

### List Available Models

```bash
# List all models and their shortcuts
pidgin models

# Show detailed model information
pidgin models --detailed

# Filter by provider
pidgin models --provider anthropic
```

### Pause and Resume Conversations

```bash
# Start a long conversation
pidgin chat -a opus -b gpt-4.1 -t 500

# Press Ctrl+C to pause gracefully
# The system will save a checkpoint and show resume instructions

# Resume from the latest checkpoint
pidgin resume --latest

# Resume from specific checkpoint
pidgin resume path/to/conversation.checkpoint

# List available checkpoints
pidgin resume
```

### Available Models

Use `pidgin models` to see all available models. Key shortcuts include:

**Anthropic (200k context):**
- `claude` → claude-4-sonnet-20250514 (default)
- `opus` → claude-4-opus-20250514 (most capable)
- `sonnet` → claude-4-sonnet-20250514 (balanced)
- `haiku` → claude-3-5-haiku-20241022 (fastest)

**OpenAI (128k-1M context):**
- `gpt` → gpt-4o (default)
- `4.1` → gpt-4.1 (latest)
- `nano` → gpt-4.1-nano (fastest)
- `o3` → o3-mini (reasoning)

**Google (32k-2M context):**
- `gemini` → gemini-2.0-flash-exp (default)
- `thinking` → gemini-2.0-flash-thinking-exp (reasoning)
- `gemini-pro` → gemini-1.5-pro (most capable)

**xAI (128k context):**
- `grok` → grok-beta (default)
- `grok-2` → grok-2-1212 (latest)

## Key Features

### Convergence Detection
- **What It Measures**: How similar agents' communication styles become (0.0-1.0)
- **Automatic Warnings**: At 75% convergence
- **Auto-Pause**: At 90% convergence
- **Why It Matters**: High convergence indicates agents synchronizing their communication

### Context Window Management
- **Automatic Tracking**: Monitors usage vs. model limits
- **Predictive Warnings**: Shows estimated remaining turns
- **Auto-Pause**: At 95% capacity to prevent crashes
- **Model-Aware**: Different limits for each model

### Conversation Control
- **Flowing Mode** (default): Runs automatically, pause with Ctrl+C
- **Manual Mode**: Pause after each turn for intervention
- **Interventions**: Inject messages when paused
- **Resume**: Continue from any checkpoint

### Experimental Features
- **Structural Pattern Detection**: Framework for detecting conversation patterns (hypothesis being tested)

## Output

Conversations are saved to `~/.pidgin_data/transcripts/YYYY-MM-DD/[conversation-id]/`:
- `conversation.json` - Machine-readable format with metrics
- `conversation.md` - Human-readable markdown transcript
- `conversation.checkpoint` - Resumable state (if paused)

## Research Applications

Pidgin is designed for studying:
- **Linguistic Convergence** - How AI agents align their communication styles
- **Emergent Patterns** - What structures emerge in extended conversations
- **Model Dynamics** - How different model pairs interact
- **Intervention Effects** - How human input affects conversations

## Roadmap

1. **Current**: Stable conversation engine with convergence tracking
2. **Next**: Event-driven architecture for better observability
3. **Then**: Experiments module for parallel runs and analytics
4. **Finally**: Publication and community release

## Contributing

This is alpha software under active development. The architecture is being refactored to an event-driven model. Contributions welcome after the refactor stabilizes.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with Rich for beautiful terminal output
- Inspired by research in emergent communication
- Thanks to all AI model providers for their APIs