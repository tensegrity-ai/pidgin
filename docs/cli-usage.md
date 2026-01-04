# CLI Usage Guide

Comprehensive guide to all Pidgin command-line interface commands and options.

## Overview

```bash
pidgin [OPTIONS] COMMAND [ARGS]...
```

Global options:
- `--help` - Show help message
- `--version` - Show version

## Commands

### `pidgin run`

Run a conversation between two AI agents.

```bash
pidgin run [OPTIONS]
```

#### Model Selection (Required unless using YAML spec)
- `-a, --agent-a MODEL` - First agent model
- `-b, --agent-b MODEL` - Second agent model

#### Optional Options
- `-p, --prompt TEXT` - Initial prompt for the conversation
- `-t, --turns INTEGER` - Maximum number of turns (default: 20)
- `-r, --repetitions INTEGER` - Number of conversations to run (default: 1)
- `--temperature FLOAT` - Temperature for both agents (0.0-2.0)
- `--temp-a FLOAT` - Temperature for agent A only
- `--temp-b FLOAT` - Temperature for agent B only
- `-w, --awareness TEXT` - Awareness level (none/basic/firm/research/backrooms) or custom YAML
- `--awareness-a TEXT` - Override awareness for agent A
- `--awareness-b TEXT` - Override awareness for agent B
- `-n, --name TEXT` - Name for the experiment (auto-generated if not provided)
- `-o, --output PATH` - Custom output directory
- `--convergence-threshold FLOAT` - Stop when convergence exceeds this (0.0-1.0)
- `--convergence-action TEXT` - Action when threshold reached (notify/pause/stop)
- `--convergence-profile TEXT` - Convergence weight profile (balanced/structural/semantic/strict)
- `--choose-names` - Let agents choose their own names
- `--show-system-prompts` - Display system prompts at start
- `--meditation` - Meditation mode: one agent faces silence
- `-q, --quiet` - Run in background with notification when complete
- `--tail` - Show formatted event stream during conversation
- `--notify` - Send notification when complete
- `--max-parallel INTEGER` - Max parallel conversations (default: 1, sequential)
- `--prompt-tag TEXT` - Tag to prefix initial prompt (default: "[HUMAN]", use "" to disable)
- `--allow-truncation` - Allow messages to be truncated to fit context windows

#### Extended Thinking Options (Claude models only)
- `--think` - Enable extended thinking for both agents
- `--think-a` - Enable extended thinking for agent A only
- `--think-b` - Enable extended thinking for agent B only
- `--thinking-budget INTEGER` - Max thinking tokens (1000-100000, default: 10000)

See [Extended Thinking](extended-thinking.md) for details.

#### Examples

```bash
# Basic conversation
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 10

# With custom prompt
pidgin run -a claude -b gpt -t 20 \
  -p "What patterns emerge in nature?"

# Watch conversation messages (verbose mode)
pidgin run -a claude -b gpt -t 30 --verbose

# With custom temperatures
pidgin run -a claude -b gpt -t 30 \
  --temp-a 0.9 \
  --temp-b 0.5

# Custom awareness levels
pidgin run -a claude -b gpt -t 15 \
  --awareness-a basic \
  --awareness-b research

# Run multiple conversations
pidgin run -a claude -b gpt -r 10 --name my_experiment

# Long conversation with message truncation enabled
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 100 \
  --allow-truncation \
  -p "Let's explore the nature of reality"

# Enable extended thinking for complex reasoning
pidgin run -a claude -b claude --think -t 15 \
  -p "Solve this step by step"

# Meditation mode: one agent faces silence
pidgin run -a claude -b claude --meditation -t 20
```

### Running from YAML Specifications

```bash
pidgin run experiment.yaml
```

#### Example YAML Specification

```yaml
name: consciousness-study
agent_a: claude-3-opus
agent_b: gpt-4
max_turns: 50
repetitions: 10
temperature_a: 0.7
temperature_b: 0.9
convergence_threshold: 0.85
prompt: "What is consciousness?"
```

### `pidgin branch`

Branch a conversation from any point with parameter changes.

```bash
pidgin branch CONVERSATION_ID [OPTIONS]
```

#### Options
- `-t, --turn INTEGER` - Turn number to branch from (default: last turn)
- `-a, --agent-a MODEL` - Override agent A model
- `-b, --agent-b MODEL` - Override agent B model
- `--temperature FLOAT` - Override temperature for both agents
- `--temp-a FLOAT` - Override temperature for agent A
- `--temp-b FLOAT` - Override temperature for agent B
- `-w, --awareness TEXT` - Override awareness level or YAML file
- `--awareness-a TEXT` - Override awareness for agent A
- `--awareness-b TEXT` - Override awareness for agent B
- `--max-turns INTEGER` - Override maximum turns
- `-n, --name TEXT` - Name for the branched experiment
- `-r, --repetitions INTEGER` - Number of branches to create (default: 1)
- `-q, --quiet` - Run in background
- `-s, --spec PATH` - Save branch configuration as YAML spec

#### Examples

```bash
# Branch from turn 10 with different models
pidgin branch cosmic-prism 10 \
  --model-a claude-3-opus \
  --model-b gpt-4-turbo \
  --turns 20

# Branch with custom prompt
pidgin branch experiment_abc123 25 \
  --prompt "Let's explore this differently" \
  --turns 15
```

### `pidgin monitor`

Live system health monitor that reads directly from JSONL files.

```bash
pidgin monitor
```

#### Display Panels

The monitor shows a multi-panel dashboard:

**Header**
- Rotating refresh indicator
- Current timestamp
- Active experiment count

**Summary Panel**
- Total experiments (active/completed/failed)
- Aggregate token usage and costs
- Overall progress percentage

**Experiments Panel**
- Each active experiment with:
  - Name and ID
  - Progress (conversations completed / total)
  - Status (running, paused, completing)

**Conversations Panel**
- Active conversations with:
  - Current turn number
  - Agent models
  - Latest convergence score
  - Token usage

**Errors Panel** (when errors occur)
- Recent API errors
- Rate limit events
- Timeout events

#### Behavior

- **Refresh rate**: Updates every 1-2 seconds
- **Lock-free**: Reads directly from JSONL files, no database locks
- **Dynamic width**: Adjusts to terminal size (60-150 chars)
- **Exit**: Press Ctrl+C to exit

#### Example Output

```
╭─ Pidgin Monitor ─────────────────────────────────────╮
│ ◐ 14:23:45                          2 experiments    │
╰──────────────────────────────────────────────────────╯

╭─ Active Experiments ─────────────────────────────────╮
│ consciousness-study    ████████░░ 8/10 conversations │
│ language-patterns      ██░░░░░░░░ 2/10 conversations │
╰──────────────────────────────────────────────────────╯

╭─ Conversations ──────────────────────────────────────╮
│ conv_abc123  Turn 15/50  claude↔gpt  conv: 0.342     │
│ conv_def456  Turn 8/50   claude↔gpt  conv: 0.187     │
╰──────────────────────────────────────────────────────╯
```

### `pidgin stop`

Gracefully stop running experiments.

```bash
pidgin stop [TARGET] [OPTIONS]
```

#### Options
- `--all` - Stop all experiments
- `--force` - Force immediate stop

#### Examples

```bash
# Stop specific experiment
pidgin stop cosmic-prism

# Stop all running experiments
pidgin stop --all

# Force stop
pidgin stop experiment_abc --force
```

### `pidgin models`

List available AI models grouped by provider.

```bash
pidgin models [OPTIONS]
```

#### Options
- `--all` - Show all stable production models (default shows only curated models)

#### Output Format

Models are grouped by provider and show:
- Model name and aliases
- Context window size
- Cost per million tokens (input/output)

#### Example Output

```
╭─ Anthropic ──────────────────────────────────────────╮
│ claude-3-5-sonnet  (claude, sonnet)   200K  $3/$15   │
│ claude-3-haiku     (haiku)            200K  $0.25/$1 │
│ claude-3-opus      (opus)             200K  $15/$75  │
╰──────────────────────────────────────────────────────╯

╭─ OpenAI ─────────────────────────────────────────────╮
│ gpt-4o             (gpt)              128K  $5/$15   │
│ gpt-4o-mini        (mini)             128K  $0.15/$0 │
╰──────────────────────────────────────────────────────╯

╭─ Local ──────────────────────────────────────────────╮
│ local:test         (test)             4K    free     │
│ ollama:llama3.2    (llama)            128K  free     │
╰──────────────────────────────────────────────────────╯
```

#### Ollama Integration

If Ollama is installed, locally available models are automatically detected and listed under the "Local" section. Models can be referenced as `ollama:model-name`.

### `pidgin config`

Create a configuration file with example settings.

```bash
pidgin config [OPTIONS]
```

#### Options
- `-f, --force` - Overwrite existing configuration file

#### Configuration File Location

Creates `~/.config/pidgin/pidgin.yaml` with default settings.

#### Example Configuration

```yaml
# Default models
default_agent_a: claude-3-5-sonnet
default_agent_b: gpt-4o

# Default parameters
default_turns: 20
default_temperature: 0.7

# Output settings
output_dir: ~/pidgin_output

# Display preferences
default_display_mode: progress
show_costs: true

# Rate limiting
max_parallel: 1
rate_limit_buffer: 0.1

# Notifications
notify_on_complete: true
notify_on_error: true
```

#### Environment Variable Override

Configuration values can be overridden with environment variables:

```bash
export PIDGIN_OUTPUT_DIR=/custom/path
export PIDGIN_MAX_PARALLEL=4
```

## Display Modes

### Progress (Default)
Shows a live-updating panel with:
- Turn counter and convergence score
- Message previews
- Token usage and costs

### Verbose
Displays complete messages as they arrive:
```
[agent_a] The nature of consciousness presents a fundamental...
[agent_b] Indeed, the hard problem of consciousness remains...
```

### Tail
Like `tail -f` for conversations:
```
[12:34:56] Turn 5 | Conv: 0.234 | agent_a: "The recursive nature..."
[12:35:02] Turn 5 | Conv: 0.234 | agent_b: "Indeed, the paradox..."
```

### Monitor
Minimal output for background runs:
```
Started: cosmic-prism
Turn 10/50 complete
Turn 20/50 complete
```

## Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
XAI_API_KEY=...

# Output directory (default: ./pidgin_output)
PIDGIN_OUTPUT_DIR=/path/to/output

# Default display mode
PIDGIN_DISPLAY_MODE=chat

# Parallel conversation limit
PIDGIN_MAX_PARALLEL=4
```

## Advanced Usage

### Pipe to Other Tools

```bash
# Extract just messages
pidgin run -a claude -b gpt -t 10 --display monitor | \
  grep "agent_" > messages.txt

# Watch for specific patterns
pidgin run -a claude -b gpt -t 50 --display tail | \
  grep -i "consciousness"
```

### Custom Model Routing

Use model prefixes for different providers:
- `anthropic:claude-3-sonnet`
- `openai:gpt-4`
- `google:gemini-pro`
- `xai:grok-beta`
- `local:llama2`

### Checkpoint and Resume

```bash
# Run with checkpoints every 10 turns
pidgin run -a claude -b gpt -t 100 --checkpoint-every 10

# If interrupted, creates checkpoint files
# Resume from checkpoint (not yet implemented)
```

## Tips and Best Practices

1. **Start Small**: Test with 5-10 turns before long runs
2. **Use Cheap Models**: Development with haiku/mini models
3. **Monitor Costs**: Watch token usage in progress panel
4. **Save Specifications**: Use YAML files for reproducibility
5. **Branch Interesting Moments**: Explore alternate paths
6. **Background Long Runs**: Use `--daemon` for experiments

## Troubleshooting

### Command Not Found
Ensure Pidgin is in your PATH:
```bash
which pidgin
export PATH="$HOME/.local/bin:$PATH"
```

### API Key Errors
Check your keys are set:
```bash
# Check API keys in environment
env | grep API_KEY
```

### Model Not Found
List available models:
```bash
pidgin models
```

### Output Directory Issues
Set custom output location:
```bash
export PIDGIN_OUTPUT_DIR=/path/to/output
```

## See Also

- [Extended Thinking](extended-thinking.md) - Claude reasoning traces
- [Analysis & Notebooks](analysis.md) - Post-experiment analysis
- [YAML Specifications](yaml-specs.md) - Detailed YAML format
- [Custom Awareness](custom-awareness.md) - Awareness prompts
- [Database](database.md) - DuckDB schema and queries
- [Metrics](metrics.md) - Available metrics
- [API Reference](api/index.md) - Python API documentation