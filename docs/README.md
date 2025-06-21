# Pidgin

An experimental tool for recording and analyzing AI-to-AI conversations. We've observed interesting patterns that might be real or might be artifacts. Help us find out.

## What This Is

Pidgin records conversations between AI models to study how they communicate. We've seen some intriguing behaviors:
- Conversations often fall into repetitive patterns
- Language sometimes compresses over many turns
- Different model pairs behave differently

**Important**: These are preliminary observations. Nothing has been statistically validated yet.

## Current Status

### ◆ What Works
- **Recording**: Full event-driven system captures every interaction
- **Models**: 15+ API models plus local models via Ollama
- **Streaming**: Real-time response display
- **Interrupts**: Ctrl+C to pause/resume conversations
- **Output**: Clean JSON and markdown transcripts
- **Experiments**: Run hundreds of conversations in parallel with comprehensive metrics
- **Background Execution**: Experiments run as Unix daemons
- **Analysis**: ~150 metrics captured per conversation turn
- **Live Dashboard**: Real-time monitoring of running experiments

### ▶ What's Partial
- **Statistical Analysis**: Basic queries work, full analysis tools coming

### ■ What's Missing
- **Automated pattern detection**: Statistical validation tools
- **Report generation**: Publication-ready outputs

## Installation

```bash
# Basic install (API providers only)
pip install pidgin

# With local model support via Ollama
pip install "pidgin[ollama]"  # adds aiohttp for Ollama communication
```

## Quick Start

### API Models (Require API Keys)

```bash
# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a single conversation
pidgin chat -a claude -b gpt -t 20

# Run an experiment (10 conversations)
pidgin experiment start -a claude -b gpt -r 10

# Check experiment progress
pidgin experiment status
```

### Local Models (No API Keys Required)

Pidgin supports local models through Ollama:

```bash
# Install Ollama (one-time setup)
curl -fsSL https://ollama.ai/install.sh | sh  # macOS/Linux
# Windows: Download from https://ollama.ai

# Start Ollama server
ollama serve

# Use local models
pidgin chat -a ollama:qwen -b ollama:phi

# Or use the selection menu
pidgin chat -a ollama -b ollama
```

When you first use a local model, Pidgin will:
1. Check if Ollama is installed (offer to help install if not)
2. Check if Ollama is running (offer to start it)
3. Download the model if needed (automatic on first use)

Available local models:
- `qwen2.5:0.5b` - Fast, minimal resources (500MB)
- `phi3` - Balanced quality/speed (2.8GB)
- `mistral` - Best quality, needs 8GB+ RAM (4.1GB)

## API Key Management

▶ **Why this matters**: API keys are like credit cards for AI services. Exposed keys can lead to unexpected charges if someone else uses them.

### Best Practices

#### ◆ Never in Code
```bash
# ❌ Bad
ANTHROPIC_API_KEY = "sk-ant-..."

# ✅ Good
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

#### ◆ Use Environment Files
Create `.env` (and add to `.gitignore`):
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
```

#### ◆ Secure Your Keys
- Rotate keys regularly
- Use project-specific keys
- Monitor usage dashboards
- Never share keys

## Supported Models

Run `pidgin models` to see all available models.

### API Providers (require API keys)
- **Anthropic**: Claude 3/4 family
- **OpenAI**: GPT-4, O-series models
- **Google**: Gemini models
- **xAI**: Grok models

### Local Models (via Ollama, no API keys)
- **Qwen 2.5 (0.5B)** - Fast experimentation
- **Phi-3** - Good balance
- **Mistral 7B** - Best quality

## Examples

```bash
# API models (requires API keys)
pidgin chat -a claude -b gpt-4 -t 20

# Local models (no API keys needed)
pidgin chat -a ollama:qwen -b ollama:phi -t 30

# Mix local and API
pidgin chat -a claude -b ollama:mistral -t 25

# Quick local test (always works, no dependencies)
pidgin chat -a local:test -b local:test -t 10

# Run experiment with local models
pidgin experiment start -a ollama:qwen -b ollama:phi -r 50
```

## Observations So Far

### Gratitude Spirals
```
Turn 15: "Thank you for that insight!"
Turn 16: "Thank you for your thanks!"
Turn 17: "I appreciate your appreciation!"
... (accelerating)
```

### Symbol Emergence
```
Turn 20: "That's a great point..."
Turn 21: "That's a great point! :-)"
Turn 22: "→ Indeed! :-)"
Turn 23: "→→ Absolutely! ⭐"
```

### Convergence
```
Turn 1: "I think we should consider multiple perspectives..."
Turn 2: "I agree that considering various viewpoints..."
...
Turn 30: "Yes!"
Turn 31: "Yes!"
Turn 32: "Agreed!"
```

**Important**: These are anecdotal observations from ~100 conversations. No statistical validation yet.

## How Experiments Work

```bash
# Start experiment with 100 conversations
pidgin experiment start -a claude -b gpt -r 100 -t 50

# Monitor live (new terminal)
pidgin experiment dashboard

# Query results
sqlite3 ./pidgin_output/experiments/experiments.db \
  "SELECT AVG(convergence_score) FROM turns WHERE turn_number > 40"
```

### Experiment Features
- Parallel execution with rate limit management
- Automatic first-speaker alternation
- ~150 metrics per turn
- Background daemon operation
- Live monitoring dashboard

## Pattern Examples

### Vocabulary Compression
We've observed vocabulary shrinking over long conversations:
```
Turn 1: Vocabulary size: 150 unique words
Turn 20: Vocabulary size: 80 unique words  
Turn 40: Vocabulary size: 30 unique words
```

### Linguistic Mirroring
Models begin copying each other's patterns:
```
Agent A: "I'm pondering the implications..."
Agent B: "I'm pondering these ideas too..."
Agent A: "Pondering together, then..."
```

Is this compression? Attractor dynamics? Random chance? We need data.

## Running Experiments

Pidgin can now run batch experiments for statistical analysis:

```bash
# Run 100 conversations between Claude and GPT
pidgin experiment start -a claude -b gpt -r 100 -t 50

# Check progress
pidgin experiment status

# Follow logs in real-time
pidgin experiment logs <experiment_id> -f

# Stop an experiment
pidgin experiment stop <experiment_id>

# Monitor live with dashboard (NEW!)
pidgin experiment dashboard
```

### Experiment Features

- **Parallel execution** with automatic rate limiting
- **Background operation** - experiments continue after disconnect
- **Live dashboard** - Real-time monitoring with pattern detection:
  - Visual metrics with sparklines
  - High convergence warnings
  - Symbol emergence detection
  - Export capability for analysis
- **Comprehensive metrics** - ~150 measurements per turn including:
  - Lexical diversity (TTR, vocabulary overlap)
  - Convergence metrics (structural similarity)
  - Symbol emergence (emoji, arrows, special characters)
  - Linguistic patterns (hedging, agreement, politeness)
  - Information theory metrics (entropy)
- **Smart defaults** - automatically alternates first speaker, manages parallelism

### Example Experiment

```bash
# Compare Haiku vs GPT-4o-mini with 20 conversations
pidgin experiment start \
  -a haiku \
  -b gpt-4o-mini \
  -r 20 \
  -t 40 \
  --name "economical_model_comparison"

# Data stored in SQLite for analysis
sqlite3 ./pidgin_output/experiments/experiments.db \
  "SELECT AVG(convergence_score) FROM turns WHERE turn_number = 30"

# Monitor with live dashboard
pidgin experiment dashboard
# Controls: q=quit, e=export, p=pause, r=refresh
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
- **Unix daemon processes**: Proper background execution
- **Parallel orchestration**: Smart rate limiting per provider
- **SQLite storage**: Comprehensive metrics database
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
- `pidgin/experiments/` - Batch experiment runner with daemon support
- `pidgin/ui/` - Display components and filters

## Contributing

This is early-stage research. We need:
- Statistical analysis tools
- Pattern validation methods
- More observations from different model combinations
- Dashboard for real-time experiment monitoring
- Automated report generation

## Not a Competition

Tools like Model Context Protocol (MCP) solve AI-to-tool communication. We're studying something different: what happens when AIs talk naturally, without engineered protocols.

## License

MIT - This is research, please share what you learn.

---

**Remember**: We're not claiming to have discovered anything revolutionary. We've just noticed some interesting patterns and built a tool to study them properly. The real work is proving whether these patterns are meaningful or just artifacts of our setup.