# Pidgin

An experimental tool for recording and analyzing AI-to-AI conversations. We've observed interesting patterns that might be real or might be artifacts. Help us find out.

## What This Is

Pidgin records conversations between AI models to study how they communicate. We've seen some intriguing behaviors:
- Conversations often fall into repetitive patterns
- Language sometimes compresses over many turns
- Different model pairs behave differently

**Important**: These are preliminary observations. Nothing has been statistically validated yet.

## Current Status

### ✅ What Works
- **Recording**: Full event-driven system captures every interaction
- **Models**: 15+ models across Anthropic, OpenAI, Google, xAI
- **Streaming**: Real-time response display
- **Interrupts**: Ctrl+C to pause/resume conversations
- **Output**: Clean JSON and markdown transcripts
- **Experiments**: Run hundreds of conversations in parallel with comprehensive metrics
- **Background Execution**: Experiments run as Unix daemons
- **Analysis**: ~150 metrics captured per conversation turn

### 🚧 What's Partial
- **Live Dashboard**: Coming in Phase 4
- **Statistical Analysis**: Basic queries work, full analysis tools coming

### ❌ What's Missing
- **Rich dashboard visualization**: Real-time experiment monitoring
- **Automated pattern detection**: Statistical validation tools
- **Report generation**: Publication-ready outputs

## Quick Start

```bash
# Install
pip install -e .

# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a single conversation
pidgin chat -a claude -b gpt -t 20

# Run an experiment (10 conversations)
pidgin experiment start -a claude -b gpt -r 10

# Check experiment progress
pidgin experiment status

# Output saved to ./pidgin_output/
```

## Why This Matters

When AIs talk to each other millions of times daily, do they develop more efficient protocols? We don't know. That's what we're trying to find out.

## Examples of What We've Seen

```
Turn 1: "Hello! How are you today?"
Turn 2: "I'm doing well, thank you! How are you?"
...
Turn 30: "Grateful!"
Turn 31: "Grateful too!"
Turn 32: "🙏"
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
```

### Experiment Features

- **Parallel execution** with automatic rate limiting
- **Background operation** - experiments continue after disconnect
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