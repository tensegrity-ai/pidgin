# Pidgin

[![CI](https://github.com/tensegrity-ai/pidgin/actions/workflows/ci.yml/badge.svg)](https://github.com/tensegrity-ai/pidgin/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A research tool for running and recording conversations between two AI models. Pidgin drives the turn-by-turn exchange, streams each message to disk as structured events, and produces JSONL transcripts and a DuckDB database for later analysis.

It was built to study a behavior noted in Anthropic's research on Claude self-interaction: extended model-to-model conversations sometimes fall into narrow attractor basins — repetitive, compressed, or stylized exchanges that diverge sharply from how the models behave with a human interlocutor. Pidgin provides the instrumentation to reproduce, vary, and measure those dynamics across model pairs and prompt conditions.

## Quick Start

```bash
# Install
uv tool install pidgin-ai      # or: pipx install pidgin-ai

# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a conversation
pidgin run -a opus -b gpt-4o -t 20

# See available models
pidgin models
```

Output is saved to `./pidgin_output/`.

## Status

### ◆ Implemented
- **Providers**: Anthropic, OpenAI, Google, xAI, and local models via Ollama (20+ models total)
- **Recording**: JSONL event log per conversation, markdown transcripts, manifest-tracked state
- **Display modes**: chat bubbles (default), raw event stream (`--tail`), quiet/background (`-q`)
- **Batch experiments**: repeat a conversation N times under a single experiment name
- **YAML specs**: define experiments as config files
- **Extended thinking**: capture Claude's reasoning traces with `--think`
- **Awareness presets**: system-prompt templates (`basic`, `research`, `backrooms`, `none`, or custom YAML)
- **Branching**: fork a new conversation from any turn of an existing one
- **Analysis**: ~150 metrics per turn imported to DuckDB on experiment completion
- **Monitoring**: `pidgin monitor` for running experiments; standard Unix tools work on the JSONL files

### ▶ Partial
- **Metrics**: placeholder columns exist for semantic similarity and sentiment; compute post-hoc
- **Parallelism**: architecture supports it, but sequential execution is the default to respect rate limits

### ■ Not implemented
- Multi-modal inputs (text only)
- More than two participants per conversation

## Usage

```bash
# Default chat display
pidgin run -a sonnet -b gpt-4o -t 20

# Raw event stream
pidgin run -a sonnet -b gpt-4o -t 20 --tail

# Background with desktop notification on completion
pidgin run -a sonnet -b gpt-4o -t 20 -q

# Custom initial prompt
pidgin run -a opus -b gemini -t 30 -p "Discuss emergence in complex systems"

# Repeat 20 times under a named experiment
pidgin run -a haiku -b gpt-4o-mini -r 20 --name my_experiment

# Run from a YAML spec
pidgin run experiment.yaml

# Monitor running experiments
pidgin monitor

# Stop an experiment
pidgin stop my_experiment

# Fork a conversation from turn 10
pidgin branch conv_abc123 --turn 10
```

### Awareness levels

System prompts that frame the conversational context:

```bash
pidgin run -a opus -b gpt-4o -w basic       # "You are an AI talking to another AI"
pidgin run -a opus -b gpt-4o -w research    # Named models, research framing
pidgin run -a opus -b gpt-4o -w backrooms   # Liminal exploration, ascii art welcome
pidgin run -a opus -b gpt-4o -w none        # No system prompt
pidgin run -a opus -b gpt-4o -w custom.yaml # Turn-based prompt injection
```

See [docs/custom-awareness.md](docs/custom-awareness.md) for the YAML format.

### Extended thinking

```bash
pidgin run -a opus -b sonnet --think -t 15
pidgin run -a opus -b gpt-4o --think-a --thinking-budget 20000
```

See [docs/extended-thinking.md](docs/extended-thinking.md).

### YAML specifications

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

### Local models

```bash
pidgin run -a local:qwen -b local:phi
```

Pidgin installs Ollama and pulls the model on first use. Available: `local:qwen` (500MB), `local:phi` (2.8GB), `local:mistral` (4.1GB), `local:test` (no download, pattern-based).

## Data layout

JSONL files are the source of truth; DuckDB is built from them.

```
pidgin_output/
  experiments/
    my-experiment_a1b2c3d4/
      manifest.json           # Experiment state
      events_conv_xxx.jsonl   # All events per conversation
      transcript_summary.md   # Readable transcript
  experiments.duckdb          # Analytics (auto-imported on completion)
```

Standard tools work directly on the event files:

```bash
tail -f pidgin_output/experiments/my-experiment_*/events_*.jsonl
cat events_*.jsonl | jq 'select(.event_type == "MessageCompleteEvent") | .message.content'
```

The DuckDB database is only built after an experiment finishes; until then, the JSONL files are current.

## Architecture

```
Conductor → EventBus → Components
              ↓
         JSONL files
              ↓
        manifest.json
              ↓
     DuckDB (post-import)
```

- **Event-driven core**: every significant action emits a typed event on the bus; components subscribe to what they care about
- **Provider abstraction**: each model provider implements a single `stream_response` interface
- **EventStore**: the only component that reads from DuckDB; all analytics go through its API

Key modules:

- `pidgin/core/` — event bus, conductor, conversation orchestration
- `pidgin/providers/` — API clients for each provider
- `pidgin/metrics/` — per-turn metric calculation
- `pidgin/experiments/` — batch runner with background-process support
- `pidgin/ui/` — display modes and filters

## Development

```bash
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin
uv sync
uv run pidgin --help
uv run pytest
```

## Acknowledgments

- [liminalbardo/liminal_backrooms](https://github.com/liminalbardo/liminal_backrooms) — inspiration for the `backrooms` awareness preset

## License

MIT
