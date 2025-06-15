# Pidgin

AI conversation research tool for studying emergent communication between language models.

## Overview

Pidgin enables controlled experiments between AI agents to study their communication patterns. It features a fully event-driven architecture, real-time streaming, and the ability to pause conversations with Ctrl+C.

## What's Actually Working ✅

- **Event-driven architecture** - Every action emits observable events
- **Conversation streaming** - Real-time responses from all providers  
- **Pause/Resume** - Press Ctrl+C to pause any conversation
- **Multi-provider support** - 15+ models from Anthropic, OpenAI, Google, xAI
- **Structured output** - Conversations saved with full event logs
- **Dimensional prompts** - Quick conversation setup system

## What's In Progress 🚧

- **Convergence detection** - Metrics are calculated but not displayed/used
- **Context window tracking** - Code exists but isn't active
- **Message injection** - Can pause but can't inject messages yet

## What's Planned 📋

- **Batch experiments** - Run multiple conversations in parallel
- **Live dashboard** - Real-time monitoring with Rich
- **Pattern analysis** - Discover emergent behaviors
- **Event replay** - Resume conversations from event logs

## Installation

### Prerequisites

- Python 3.9 or higher
- API keys for the providers you want to use

### Install from source

```bash
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin
pip install -e .
```

### Set API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."
```

## Quick Start

### Basic Usage

```bash
# Simple conversation
pidgin chat -a claude -b gpt -t 20

# With custom prompt
pidgin chat -a opus -b gpt-4.1 -p "Discuss mathematics"

# Using dimensional prompts
pidgin chat -d peers:philosophy

# Let agents choose names
pidgin chat -a haiku -b nano --choose-names
```

### Pause/Resume

During any conversation, press `Ctrl+C` to pause:
1. The current message will complete
2. A menu appears with Continue/Exit options
3. All data is saved automatically

### Output Files

Conversations are saved to `./pidgin_output/conversations/YYYY-MM-DD/[id]/`:
- `events.jsonl` - Complete event log (every action recorded)
- `conversation.json` - Structured conversation data
- `conversation.md` - Human-readable transcript

## Available Models

Use `pidgin models` to see all available models. Common shortcuts:
- `claude` → claude-4-sonnet (default)
- `opus` → claude-4-opus (most capable)
- `haiku` → claude-3-5-haiku (fastest)
- `gpt` → gpt-4o
- `gemini` → gemini-2.0-flash-exp

## Architecture

Pidgin is built on an event-driven architecture where:
- Every action emits an event
- Events are logged to JSONL for analysis
- Components communicate only through events
- No hidden state or side effects

## Research Focus

We're building tools to observe what happens when AIs communicate, without assuming what we'll find. Current areas of investigation:

- How do conversation patterns evolve over many turns?
- Do certain model pairs develop unique dynamics?
- What happens during very long conversations?
- How do interruptions affect conversation flow?

## Contributing

This is alpha software under active development. The architecture is stabilizing but features are still being added.

## License

MIT License - see LICENSE file for details.