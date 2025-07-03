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
- **Models**: 15+ models across Anthropic, OpenAI, Google, xAI
- **Streaming**: Real-time response display
- **Interrupts**: Ctrl+C to pause/resume conversations
- **Output**: Clean JSON and markdown transcripts
- **Experiments**: Run hundreds of conversations with comprehensive metrics (sequential execution by default)
- **Background Execution**: Experiments run as Unix daemons
- **Analysis**: ~150 metrics captured per conversation turn
- **Database**: SQLite for storage (DuckDB migration planned)

### ▶ What's Partial
- **Statistical Analysis**: Basic queries work, full analysis tools coming
- **Jupyter Integration**: Auto-generated notebooks planned

### ■ What's Missing
- **Automated pattern detection**: Statistical validation tools
- **Report generation**: Publication-ready outputs
- **GraphQL interface**: Flexible querying for research

## Quick Start

```bash
# Install
pip install -e .

# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a single conversation
pidgin chat -a claude -b gpt -t 20

# Run with notification when complete
pidgin chat -a claude -b gpt -t 20 --notify

# Run in quiet mode (minimal output)
pidgin chat -a claude -b gpt -t 20 --quiet

# Run an experiment (10 conversations)
pidgin experiment start -a claude -b gpt -r 10 --name my_experiment

# Check experiment progress
pidgin experiment status my_experiment

# Watch progress with notifications
pidgin experiment status my_experiment --watch --notify

# Output saved to ./pidgin_output/
```

## API Key Management

▶ **Why this matters**: API keys are like credit cards for AI services. Exposed keys can lead to unexpected charges if someone else uses them.

For better security, we recommend using a key manager rather than environment variables:

### Using 1Password CLI (Recommended)
```bash
# Install 1Password CLI
brew install --cask 1password-cli

# Run Pidgin with keys from 1Password
op run --env-file=.env.1password -- pidgin chat -a claude -b gpt

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

### Other Options
- **AWS Secrets Manager** - For cloud deployments
- **HashiCorp Vault** - For enterprise environments
- **age** - Modern encryption tool for secrets

■ **Never commit API keys to git**, even in private repositories.

## Local Models

Pidgin supports running models locally on your machine:

```bash
# Quick start - Pidgin handles everything
pidgin chat -a local -b local

# Or specify models directly
pidgin chat -a local:qwen -b local:phi
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

When AIs talk to each other millions of times daily, do they develop more efficient protocols? We don't know. That's what we're trying to find out.

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
pidgin experiment start -a claude -b gpt -r 100 -t 50 --name language_study

# Check progress
pidgin experiment status language_study

# Watch progress with notifications
pidgin experiment status language_study --watch --notify

# List all experiments
pidgin experiment list

# Stop an experiment
pidgin experiment stop language_study
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
pidgin experiment start \
  -a haiku \
  -b gpt-4o-mini \
  -r 20 \
  -t 40 \
  --name "economical_model_comparison"

# Check status
pidgin experiment status economical_model_comparison

# Data stored in SQLite currently
# (Coming soon: DuckDB migration and GraphQL interface)
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
- **Sequential orchestration**: Rate limit aware execution
- **SQLite storage**: Current database (DuckDB migration planned)
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
- Automated report generation
- GraphQL interface for flexible querying

## Not a Competition

Tools like Model Context Protocol (MCP) solve AI-to-tool communication. We're studying something different: what happens when AIs talk naturally, without engineered protocols.

## License

MIT - This is research, please share what you learn.

---

**Remember**: We're not claiming to have discovered anything revolutionary. We've just noticed some interesting patterns and built a tool to study them properly. The real work is proving whether these patterns are meaningful or just artifacts of our setup.