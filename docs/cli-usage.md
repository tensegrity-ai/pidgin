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

#### Required Options
- `-a, --agent-a MODEL` - Model for agent A
- `-b, --agent-b MODEL` - Model for agent B  
- `-t, --turns INTEGER` - Number of turns

#### Optional Options
- `-p, --prompt TEXT` - Initial prompt (default: dimensional question)
- `--awareness-a TEXT` - Agent A's awareness level
- `--awareness-b TEXT` - Agent B's awareness level
- `--temperature-a FLOAT` - Override agent A temperature
- `--temperature-b FLOAT` - Override agent B temperature
- `--display MODE` - Display mode: `progress`, `chat`, `tail`, `monitor`
- `--name TEXT` - Custom experiment name
- `--output PATH` - Output directory
- `--no-conversation` - Skip initial "Hello" exchange
- `--checkpoint-every INT` - Save checkpoint every N turns
- `--allow-truncation` - Allow messages to be truncated to fit context windows (default: disabled)
- `--info` - Show configuration and exit

#### Examples

```bash
# Basic conversation
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 10

# With custom prompt
pidgin run -a claude -b gpt -t 20 \
  -p "What patterns emerge in nature?"

# Chat output with custom temperatures
pidgin run -a claude -b gpt -t 30 \
  --display chat \
  --temperature-a 0.9 \
  --temperature-b 0.5

# Custom awareness prompts
pidgin run -a claude -b gpt -t 15 \
  --awareness-a "You are exploring mathematics" \
  --awareness-b "You are a curious student"

# Long conversation with message truncation enabled
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 100 \
  --allow-truncation \
  -p "Let's explore the nature of reality"
```

### `pidgin experiment`

Run batch experiments from YAML specifications.

```bash
pidgin experiment [SUBCOMMAND]
```

#### Subcommands

##### `run`
```bash
pidgin experiment run SPEC_FILE [OPTIONS]
```

Options:
- `--parallel INT` - Number of parallel conversations
- `--name TEXT` - Experiment name
- `--daemon` - Run as background daemon

##### `status`
```bash
pidgin experiment status [NAME]
```

##### `stop`
```bash
pidgin experiment stop NAME
```

#### Example YAML Specification

```yaml
name: consciousness-study
parallel: 2
conversations:
  - agent_a: claude-3-sonnet
    agent_b: gpt-4
    turns: 50
    initial_prompt: "What is consciousness?"
    temperature_a: 0.7
    temperature_b: 0.7
  
  - agent_a: claude-3-opus
    agent_b: gpt-4-turbo
    turns: 50
    initial_prompt: "What is consciousness?"
    temperature_a: 0.9
    temperature_b: 0.9
```

### `pidgin branch`

Create a new conversation branch from an existing turn.

```bash
pidgin branch SOURCE_PATH TURN_NUMBER [OPTIONS]
```

#### Options
- `--model-a MODEL` - New model for agent A
- `--model-b MODEL` - New model for agent B
- `--turns INTEGER` - Additional turns to run
- `--prompt TEXT` - Override next message
- `--display MODE` - Display mode

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

System-wide monitoring dashboard.

```bash
pidgin monitor [OPTIONS]
```

#### Options
- `--interval SECONDS` - Refresh interval (default: 2)
- `--history MINUTES` - History window (default: 60)

#### Display Shows
- Active experiments
- Token usage rates
- Cost tracking
- System resources
- Recent errors

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

### `pidgin info`

Display various information about models, outputs, and configuration.

```bash
pidgin info [SUBCOMMAND]
```

#### Subcommands

##### `models`
List all available models and their details.
```bash
pidgin info models [--provider PROVIDER]
```

##### `output`
Show information about a completed conversation.
```bash
pidgin info output PATH
```

##### `costs`
Display current token costs by provider.
```bash
pidgin info costs
```

##### `api-keys`
Check which API keys are configured.
```bash
pidgin info api-keys
```

##### `commands`
List all available commands.
```bash
pidgin info commands
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
pidgin info api-keys
```

### Model Not Found
List available models:
```bash
pidgin info models
```

### Output Directory Issues
Set custom output location:
```bash
export PIDGIN_OUTPUT_DIR=/path/to/output
```

## See Also

- [YAML Specifications](yaml-specs.md) - Detailed YAML format
- [Configuration](custom-awareness.md) - Awareness prompts
- [API Reference](api/index.md) - Python API documentation