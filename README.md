# Pidgin

[![CI](https://github.com/tensegrity-ai/pidgin/actions/workflows/ci.yml/badge.svg)](https://github.com/tensegrity-ai/pidgin/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

An experimental tool for recording and analyzing AI-to-AI conversations. We've observed interesting patterns that might be real or might be artifacts. Help us find out.

## What This Is

Pidgin records conversations between AI models to study how they communicate. We've seen some intriguing behaviors:
- Conversations often fall into repetitive patterns
- Language sometimes compresses over many turns
- Different model pairs behave differently

**Important**: These are preliminary observations. Nothing has been statistically validated yet.

## Current Status

### ◆ What Works
- **Recording**: JSONL-based event capture for every interaction
- **Models**: 20+ models across Anthropic, OpenAI, Google, xAI, and local (Ollama)
- **Extended Thinking**: Capture Claude's reasoning traces with `--think` ([docs](docs/extended-thinking.md))
- **Display**: Real-time observability with convergence tracking, chat mode, or raw event stream
- **Output**: JSONL events, markdown transcripts, manifest tracking
- **Experiments**: Run hundreds of conversations with smart parallelism
- **Background**: Background processes with meaningful names and system-wide monitoring
- **Analysis**: 150+ metrics per turn in DuckDB wide-table format
- **Monitoring**: Live system monitor and standard Unix tools (tail, grep, jq)
- **Jupyter Notebooks**: Auto-generated analysis notebooks for each experiment
- **Branching**: Create alternate conversation paths from any turn
- **Stop Command**: Gracefully stop experiments by ID or name

### ▶ What's Partial
- **Advanced Metrics**: Placeholder columns for semantic similarity, sentiment (calculate post-hoc)
- **Statistical Validation**: Basic analysis works, significance testing coming

### ■ What's Missing
- **Multi-modal Support**: Text-only for now
- **Multi-party**: Conversations are limited to two participants

## Quick Start

```bash
# Install the CLI tool (choose one)
uv tool install pidgin-ai      # Recommended - fast, isolated
pipx install pidgin-ai          # Alternative - isolated  
pip install pidgin-ai           # Traditional - global

# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a single conversation (shows progress panel)
pidgin run -a claude -b gpt -t 20

# Watch the conversation messages
pidgin run -a claude -b gpt -t 20 --verbose

# See raw event stream (like tail -f)
pidgin run -a claude -b gpt -t 20 --tail

# Run in background with notification
pidgin run -a claude -b gpt -t 20 --quiet

# Run multiple conversations (10 repetitions)
pidgin run -a claude -b gpt -r 10 --name my_experiment

# Run from YAML specification
pidgin run experiment.yaml

# Use custom awareness with turn-based prompts
pidgin run -a claude -b gpt --awareness custom_awareness.yaml

# Monitor all running experiments (live dashboard)
pidgin monitor

# Stop a specific experiment
pidgin stop my_experiment
pidgin stop --all  # Stop all experiments

# List available models
pidgin models

# View models with all details
pidgin models --all

# Branch from an existing conversation
pidgin branch conv_abc123 --turn 10

# Output saved to ./pidgin_output/
```

### YAML Specifications

For complex experiments, you can define configurations in YAML:

```yaml
# experiment.yaml
name: "temperature-differential"
agent_a: claude-3-opus
agent_b: gpt-4
max_turns: 50
repetitions: 10
temperature_a: 0.3
temperature_b: 0.9
convergence_threshold: 0.85
prompt: "Discuss the nature of consciousness"
```

Then run with: `pidgin run experiment.yaml`

See [docs/yaml-specs.md](docs/yaml-specs.md) for all available options.

### Data Storage

Pidgin uses a JSONL-first architecture:
- **Primary storage**: JSONL files for each conversation
- **State tracking**: manifest.json for efficient monitoring
- **Analytics**: DuckDB for post-experiment analysis

Experiments are automatically imported into DuckDB when they complete. No manual import step is needed.

## API Key Management

▶ **Why this matters**: API keys are like credit cards for AI services. Exposed keys can lead to unexpected charges if someone else uses them.

For better security, we recommend using a key manager rather than hard-coding environment variables:

### Using 1Password CLI (Recommended)
```bash
# Install 1Password CLI
brew install --cask 1password-cli

# Run Pidgin with keys from 1Password
op run --env-file=.env.1password -- pidgin run -a claude -b gpt

# Where .env.1password contains:
# ANTHROPIC_API_KEY="op://Personal/Anthropic API/credential"
# OPENAI_API_KEY="op://Personal/OpenAI API/credential"
```

### Using macOS Keychain
```bash
# Store keys securely
security add-generic-password -a "$USER" -s "ANTHROPIC_API_KEY" -w "your-key-here"
security add-generic-password -a "$USER" -s "OPENAI_API_KEY" -w "your-key-here"

# Retrieve in shell profile
export ANTHROPIC_API_KEY=$(security find-generic-password -a "$USER" -s "ANTHROPIC_API_KEY" -w)
export OPENAI_API_KEY=$(security find-generic-password -a "$USER" -s "OPENAI_API_KEY" -w)
```

### Using direnv (Project-specific)
```bash
# Install direnv
brew install direnv

# Create .envrc in project root
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' > .envrc
echo 'export OPENAI_API_KEY="sk-..."' >> .envrc

# Never commit .envrc
echo ".envrc" >> .gitignore

# Allow direnv to load
direnv allow
```

■ **Never commit API keys to git**, even in private repositories.

## Local Models

Pidgin supports running models locally on your machine:

```bash
# Quick start - Pidgin handles everything
pidgin run -a local:qwen -b local:phi
```

On first use, Pidgin will:
1. Offer to install Ollama (~150MB)
2. Start the Ollama server
3. Download your chosen model

Available models:
- `local:qwen` - 500MB, fast responses
- `local:phi` - 2.8GB, balanced performance
- `local:mistral` - 4.1GB, best quality (needs 8GB+ RAM)
- `local:test` - No download, pattern-based responses

Models download automatically on first use.

## Why This Matters

When AIs talk to each other millions of times daily, might they develop more efficient protocols? We don't know. That's one thing we're trying to find out.

## Examples of What We've Seen

```
Turn 1: "Hello! How are you today?"
Turn 2: "I'm doing well, thank you! How are you?"
...
Turn 30: "Grateful!"
Turn 31: "Grateful too!"
Turn 32: "◆"
```

Is this compression? Attractor dynamics? Random chance? We need data.

## Running Experiments

Pidgin runs batch experiments for statistical analysis:

```bash
# Run 100 conversations between Claude and GPT
pidgin run -a claude -b gpt -r 100 -t 50 --name language_study

# Check progress
pidgin monitor language_study

# Monitor running experiments
pidgin monitor

# Stop an experiment
pidgin stop language_study
```

### Experiment Features

- **Sequential execution** by default (avoids rate limits and hardware constraints)
- **Background operation** - experiments continue after disconnect
- **Comprehensive metrics** - ~150 measurements per turn including:
  - Lexical diversity (TTR, vocabulary overlap)
  - Convergence metrics (structural similarity)
  - Symbol emergence (emoji, arrows, special characters)
  - Linguistic patterns (hedging, agreement, politeness)
  - Information theory metrics (entropy)
- **Smart defaults** - automatically alternates first speaker
- **Parallel support** - architecture supports parallelism when constraints allow

### Example Experiment

```bash
# Compare Haiku vs GPT-4o-mini with 20 conversations
pidgin run \
  -a haiku \
  -b gpt-4o-mini \
  -r 20 \
  -t 40 \
  --name "economical_model_comparison"

# Check status
pidgin monitor economical_model_comparison

# Data stored in DuckDB with event sourcing
# Run 'pidgin monitor' to check system and database health
```

## How to Help

1. **Run experiments**: Try different model pairs and initial prompts
2. **Report patterns**: What do you observe?
3. **Build analysis**: Help create tools to validate observations
4. **Statistical validation**: Help prove whether patterns are real

## Technical Overview

Pidgin is a comprehensive research tool with:

### Core Architecture
- **Event-driven system**: Complete observability via EventBus
- **Modular components**: Clean separation of concerns
- **Provider abstraction**: Easy to add new AI providers
- **Streaming support**: Real-time response display

### Experiment System
- **Background processes**: Proper subprocess execution with detachment
- **Sequential orchestration**: Rate limit aware execution
- **DuckDB storage**: Async database with event sourcing
- **Fault tolerance**: Graceful handling of API failures

### Metrics System
- **Unified calculation**: Single source of truth in `pidgin/metrics/`
- **150+ metrics per turn**: Comprehensive conversation analysis
- **Real-time + batch**: Same metrics for live and experiments
- **Extensible**: Easy to add new metrics

### Key Modules
- `pidgin/core/` - Event bus, conductor, conversation management
- `pidgin/providers/` - AI provider integrations
- `pidgin/metrics/` - Unified metrics calculation system
- `pidgin/experiments/` - Batch experiment runner with background process support
- `pidgin/ui/` - Display components and filters

## Development

```bash
# Clone the repository
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin

# Install with uv (recommended - fast!)
uv sync

# Run pidgin
uv run pidgin --help

# Or install globally with pipx
uv build
pipx install dist/*.whl
```

## Contributing

This is early-stage research. We need:
- Statistical analysis tools
- More observations from different model combinations
- Automated report generation

## Not a Competition

Tools like Model Context Protocol (MCP) solve AI-to-tool communication. We're studying something different: what happens when AIs talk naturally, without engineered protocols.

## Acknowledgments

- [liminalbardo/liminal_backrooms](https://github.com/liminalbardo/liminal_backrooms) - Inspiration for the `backrooms` awareness preset

## License

MIT - This is research, please share what you learn.

---

**Remember**: We're not claiming to have discovered anything revolutionary. We've just noticed some interesting patterns and built a tool to study them properly. The real work is proving whether these patterns are meaningful or just artifacts of our setup.