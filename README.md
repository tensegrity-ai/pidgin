# Pidgin

An experimental tool for recording and studying AI-to-AI conversations. We've observed some interesting patterns, but nothing has been rigorously validated yet.

## What We Noticed

While studying AI conversations, we observed some curious patterns:
- Models sometimes develop compressed references ("the thing we discussed" → "TTD")
- Gratitude spirals where AIs thank each other excessively
- Different behavioral signatures between model pairs

These observations are **anecdotal and unvalidated**. We built Pidgin to capture these conversations properly so we can determine if the patterns are real or just artifacts.

## What Actually Works

- **Basic conversation runner** - Runs conversations between AI models
- **Event logging** - Saves events to JSONL files (whether this is useful is unclear)
- **Ctrl+C interrupt** - You can pause conversations
- **Multiple providers** - Works with Anthropic, OpenAI, Google, xAI
- **Output files** - Saves transcripts and logs to `./pidgin_output/`
- **Preset prompts** - Some built-in conversation starters

## What's Missing (Critical for Research)

- **Batch experiments** - Can only run one conversation at a time (need hundreds for statistical validity)
- **Control conditions** - No way to test against shuffled/random baselines
- **Statistical analysis** - No tools to validate if patterns are real
- **Intervention system** - Can't modify conversations mid-stream
- **Reproducibility** - Small prompt changes lead to wildly different results

## Important Context

- **Early-stage research tool** - We're still figuring out if the patterns are real
- **Chaotic system** - Tiny changes in prompts → completely different conversations
- **Not competing with MCP** - Model Context Protocol already solved AI-to-tool communication
- **Different focus** - We study natural conversation patterns, not engineering solutions
- **Event architecture** - Built to support n-agent conversations in future, currently 2-agent only

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

## Technical Architecture

Event-driven design that logs everything:
- **Event bus** - Central message passing (allows future n-agent support)
- **Providers** - Wrap different AI APIs (Anthropic, OpenAI, Google, xAI)
- **Conductor** - Manages conversation flow
- **Output system** - Saves transcripts and structured data

The architecture supports multiple agents but current implementation is 2-agent only.

## Current Status

✅ **Working**: Basic conversation recording with pause/resume
🚧 **Experimental**: Convergence metrics (unvalidated)
❌ **Not Built**: Batch experiments, statistical analysis, control conditions

## How to Help

We need collaborators to:
1. **Run experiments** - Test specific patterns across many conversations
2. **Build batch runner** - Critical missing piece for statistical validity
3. **Statistical analysis** - Determine if patterns are real or artifacts
4. **Be skeptical** - Challenge our observations with rigorous testing

## Scientific Approach

We're testing whether observed patterns in AI conversations are:
- **Real phenomena** worth studying further
- **Training artifacts** from model data
- **Statistical noise** from small samples
- **Prompt sensitivity** in chaotic systems

The only way to know is through rigorous experiments with proper controls. Until then, all observations remain preliminary.

## Core Message

We saw weird stuff in AI conversations. Built a tool to capture it. Still figuring out if it's real. Want to help?

## Contributing

Experimental software seeking collaborators for rigorous validation. Most helpful contributions:
- Batch experiment infrastructure
- Statistical analysis tools
- Control condition design
- Reproducibility testing

## License

MIT License - see LICENSE file for details.