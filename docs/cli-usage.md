# CLI Usage Guide

Comprehensive guide to all Pidgin command-line options.

## `pidgin run`

Run a conversation between two AI agents.

```bash
pidgin run [OPTIONS] [SPEC_FILE]
```

### Model Selection (required unless using YAML spec)
- `-a, --agent-a MODEL` -- First agent model
- `-b, --agent-b MODEL` -- Second agent model

### Conversation Options
- `-p, --prompt TEXT` -- Initial prompt for the conversation
- `-t, --turns INTEGER` -- Maximum turns (default: 20)
- `-r, --repetitions INTEGER` -- Number of conversations to run (default: 1)
- `--temperature FLOAT` -- Temperature for both agents (0.0-2.0)
- `--temp-a FLOAT` -- Temperature for agent A only
- `--temp-b FLOAT` -- Temperature for agent B only
- `-n, --name TEXT` -- Experiment name (auto-generated if omitted)
- `-o, --output PATH` -- Custom output directory

### Awareness Options
- `-w, --awareness TEXT` -- Awareness level (none/basic/firm/research/backrooms) or custom YAML file
- `--awareness-a TEXT` -- Override awareness for agent A
- `--awareness-b TEXT` -- Override awareness for agent B
- `--choose-names` -- Let agents choose their own names
- `--show-system-prompts` -- Display system prompts at start
- `--meditation` -- Meditation mode: one agent faces silence

### Convergence Options
- `--convergence-threshold FLOAT` -- Stop when convergence exceeds this (0.0-1.0)
- `--convergence-action TEXT` -- Action at threshold (notify/pause/stop)
- `--convergence-profile TEXT` -- Weight profile (balanced/structural/semantic/strict)

### Display Options
- `-q, --quiet` -- Run in background with notification when complete
- `--tail` -- Show raw event stream instead of chat bubbles
- `--notify` -- Send notification when complete

### Extended Thinking (Claude only)
- `--think` -- Enable for both agents
- `--think-a` -- Enable for agent A only
- `--think-b` -- Enable for agent B only
- `--think-budget INTEGER` -- Max thinking tokens (default: 10000)

### Advanced Options
- `--max-parallel INTEGER` -- Max parallel conversations (default: 1)
- `--prompt-tag TEXT` -- Tag to prefix initial prompt (default: "[HUMAN]", use "" to disable)
- `--allow-truncation` -- Allow message truncation to fit context windows

### Examples

```bash
# Basic conversation
pidgin run -a haiku -b gpt-4o-mini -t 10

# Custom prompt and temperatures
pidgin run -a opus -b gpt-4o -t 30 \
  -p "What patterns emerge in nature?" \
  --temp-a 0.9 --temp-b 0.5

# Different awareness per agent
pidgin run -a sonnet -b gpt-4o -t 15 \
  --awareness-a basic --awareness-b research

# Batch experiment
pidgin run -a sonnet -b gpt-4o -r 10 --name my_experiment

# Long conversation with truncation
pidgin run -a haiku -b gpt-4o-mini -t 100 \
  --allow-truncation \
  -p "Let's explore the nature of reality"

# Extended thinking
pidgin run -a opus -b sonnet --think -t 15

# Meditation mode
pidgin run -a opus --meditation -t 20

# From YAML spec
pidgin run experiment.yaml
```

## `pidgin branch`

Branch a conversation from any point with parameter changes.

```bash
pidgin branch CONVERSATION_ID [OPTIONS]
```

### Options
- `-t, --turn INTEGER` -- Turn to branch from (default: last turn)
- `-a, --agent-a MODEL` -- Override agent A model
- `-b, --agent-b MODEL` -- Override agent B model
- `--temperature FLOAT` -- Override temperature for both agents
- `--temp-a, --temp-b FLOAT` -- Override per-agent temperature
- `-w, --awareness TEXT` -- Override awareness level or YAML file
- `--awareness-a, --awareness-b TEXT` -- Override per-agent awareness
- `--max-turns INTEGER` -- Override maximum turns
- `-n, --name TEXT` -- Name for the branched experiment
- `-r, --repetitions INTEGER` -- Number of branches (default: 1)
- `-q, --quiet` -- Run in background
- `-s, --spec PATH` -- Save branch config as YAML

### Examples

```bash
# Branch from turn 10 with different models
pidgin branch cosmic-prism --turn 10 -a opus -b gpt-4o

# Create multiple branches
pidgin branch experiment_abc123 --turn 25 -r 5
```

## `pidgin monitor`

Live system health monitor. Reads directly from JSONL files.

```bash
pidgin monitor
```

Shows a multi-panel dashboard with active experiments, conversation progress, convergence scores, token usage, and errors. Updates every 1-2 seconds. Press Ctrl+C to exit.

## `pidgin stop`

Gracefully stop running experiments.

```bash
pidgin stop [TARGET] [OPTIONS]
```

- `--all` -- Stop all experiments
- `--force` -- Force immediate stop

```bash
pidgin stop cosmic-prism
pidgin stop --all
```

## `pidgin models`

List available AI models.

```bash
pidgin models [OPTIONS]
```

- `--all` -- Show all stable production models (default shows curated set)

## `pidgin config`

Create a configuration file at `~/.config/pidgin/pidgin.yaml`.

```bash
pidgin config [--force]
```

## Display Modes

**Chat (default)**: Message bubbles with agent colors, turn separators, and convergence tracking.

**Tail** (`--tail`): Raw event stream, like `tail -f` for conversations.

**Quiet** (`-q`): Runs in background, sends notification on completion.

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
XAI_API_KEY=...
```

## See Also

- [Extended Thinking](extended-thinking.md) -- Claude reasoning traces
- [Analysis & Notebooks](analysis.md) -- Post-experiment analysis
- [YAML Specifications](yaml-specs.md) -- Detailed YAML format
- [Custom Awareness](custom-awareness.md) -- Awareness prompts and YAML format
- [Database](database.md) -- DuckDB schema and queries
- [Metrics](metrics.md) -- Available metrics
