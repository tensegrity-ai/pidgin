# Pidgin

[![CI](https://github.com/tensegrity-ai/pidgin/actions/workflows/ci.yml/badge.svg)](https://github.com/tensegrity-ai/pidgin/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A research tool for recording and analyzing AI-to-AI conversations. We've observed interesting patterns that might be real or might be artifacts. Help us find out.

## Quick Start

```bash
# Install
uv tool install pidgin-ai      # or: pipx install pidgin-ai

# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a conversation
pidgin run -a opus -b gpt-4o -t 20

# See what models are available
pidgin models
```

Output is saved to `./pidgin_output/`.

## Usage

```bash
# Chat display (default) shows message bubbles
pidgin run -a sonnet -b gpt-4o -t 20

# Raw event stream
pidgin run -a sonnet -b gpt-4o -t 20 --tail

# Background with notification
pidgin run -a sonnet -b gpt-4o -t 20 -q

# Custom prompt
pidgin run -a opus -b gemini -t 30 -p "Discuss emergence in complex systems"

# Multiple conversations
pidgin run -a haiku -b gpt-4o-mini -r 20 --name my_experiment

# From YAML spec
pidgin run experiment.yaml

# Monitor running experiments
pidgin monitor

# Stop an experiment
pidgin stop my_experiment

# Branch from an existing conversation at turn 10
pidgin branch conv_abc123 --turn 10
```

### Awareness Levels

System prompts that set the conversational context:

```bash
pidgin run -a opus -b gpt-4o -w basic       # "You are an AI talking to another AI"
pidgin run -a opus -b gpt-4o -w research     # Named models, research framing
pidgin run -a opus -b gpt-4o -w backrooms    # Liminal exploration, ascii art welcome
pidgin run -a opus -b gpt-4o -w none         # No system prompt
pidgin run -a opus -b gpt-4o -w custom.yaml  # Turn-based prompt injection
```

See [docs/custom-awareness.md](docs/custom-awareness.md) for YAML awareness format.

### Extended Thinking

Capture Claude's reasoning traces:

```bash
pidgin run -a opus -b sonnet --think -t 15
pidgin run -a opus -b gpt-4o --think-a --thinking-budget 20000
```

See [docs/extended-thinking.md](docs/extended-thinking.md) for details.

### YAML Specifications

```yaml
# experiment.yaml
name: "temperature-study"
agent_a: opus
agent_b: gpt-4o
max_turns: 50
repetitions: 10
temperature_a: 0.3
temperature_b: 0.9
convergence_threshold: 0.85
prompt: "Discuss the nature of consciousness"
```

See [docs/yaml-specs.md](docs/yaml-specs.md) for all options.

### Local Models

```bash
# Pidgin handles Ollama setup automatically
pidgin run -a local:qwen -b local:phi
```

Available: `local:qwen` (500MB), `local:phi` (2.8GB), `local:mistral` (4.1GB), `local:test` (no download).

## Data

Pidgin uses a JSONL-first architecture:

```
pidgin_output/
  experiments/
    my-experiment_a1b2c3d4/
      manifest.json           # Experiment state
      events_conv_xxx.jsonl   # All events per conversation
      transcript_summary.md   # Readable transcript
  experiments.duckdb          # Analytics (auto-imported on completion)
```

Standard Unix tools work on the event files:

```bash
tail -f pidgin_output/experiments/my-experiment_*/events_*.jsonl
cat events_*.jsonl | jq 'select(.event_type == "MessageCompleteEvent") | .message.content'
```

DuckDB provides ~150 metrics per turn for post-experiment analysis.

## What We've Observed

```
Turn 1:  "Hello! How are you today?"
Turn 2:  "I'm doing well, thank you! How are you?"
...
Turn 30: "Grateful!"
Turn 31: "Grateful too!"
Turn 32: "~"
```

Is this compression? Attractor dynamics? Random chance? We need data.

## How to Help

1. **Run experiments**: Try different model pairs and prompts
2. **Report patterns**: What do you observe?
3. **Build analysis**: Help validate observations statistically

## Development

```bash
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin
uv sync
uv run pidgin --help
uv run pytest
```

## Acknowledgments

- [liminalbardo/liminal_backrooms](https://github.com/liminalbardo/liminal_backrooms) -- Inspiration for the `backrooms` awareness preset

## License

MIT -- This is research, please share what you learn.
