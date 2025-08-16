# Quickstart Guide

Get up and running with Pidgin in 5 minutes. This guide assumes you've already [installed Pidgin](installation.md).

## Your First Conversation

### 1. Test Installation (No API Keys Required)

Start with the built-in test model to verify everything works:

```bash
pidgin run -a local:test -b local:test -t 5
```

This runs 5 turns between two test agents that echo and transform each other's messages.

### 2. Run a Real Conversation

With API keys configured, run a conversation between Claude and GPT:

```bash
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 10 \
  -p "Let's explore the concept of emergence in complex systems"
```

**What's happening:**
- `-a claude-3-haiku`: Agent A uses Claude 3 Haiku
- `-b gpt-4o-mini`: Agent B uses GPT-4o Mini  
- `-t 10`: Run for 10 turns
- `-p "..."`: Initial prompt to start the conversation

### 3. Watch the Output

By default, Pidgin shows a progress panel with:
- Current turn number
- Real-time convergence score
- Message preview
- Token usage

```
┌─ Experiment: cosmic-prism ──────────────────────────┐
│ Turn 5/20 • Convergence: 0.234 ↑                   │
│                                                     │
│ agent_a: The recursive nature of self-reference... │
│ agent_b: Indeed, the paradox emerges when we...    │
│                                                     │
│ Tokens: 1,247 • Cost: $0.0023                     │
└─────────────────────────────────────────────────────┘
```

## Understanding Output Files

After running, find your results in `pidgin_output/`:

```
pidgin_output/
├── experiments.duckdb           # Analytics database (auto-imported)
└── cosmic-prism/
    ├── manifest.json            # Experiment metadata and state
    ├── events_conv001.jsonl     # All events for conversation 1
    ├── events_conv002.jsonl     # All events for conversation 2
    └── analysis.ipynb           # Auto-generated Jupyter notebook
```

### View the Events

```bash
# Follow live events as they happen
tail -f pidgin_output/cosmic-prism/events_*.jsonl

# Count events by type
cat pidgin_output/cosmic-prism/events_*.jsonl | \
  jq -r '.event_type' | sort | uniq -c

# Extract just the messages
cat pidgin_output/cosmic-prism/events_*.jsonl | \
  jq -r 'select(.event_type == "message_complete") | .content'
```

## Common Workflows

### Different Display Modes

```bash
# Chat mode - see full messages
pidgin run -a claude -b gpt -t 10 --display chat

# Monitor mode - minimal output  
pidgin run -a claude -b gpt -t 10 --display monitor

# Tail mode - like tail -f for conversations
pidgin run -a claude -b gpt -t 10 --display tail
```

### Context Window Management

By default, Pidgin preserves research integrity by ending conversations naturally when context limits are reached:

```bash
# Default: conversation ends when context window is full
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 100

# Enable truncation for very long conversations  
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 100 --allow-truncation
```

When a context limit is reached without truncation enabled:
- The conversation ends naturally
- You'll see a "Context Window Limit Reached" message
- The event log records this as `context_limit_reached`

This preserves the complete conversation history without artificial truncation.

### Use Specific Model Versions

```bash
# List available models
pidgin models

# Use specific versions
pidgin run -a claude-3-5-sonnet-20241022 -b gpt-4-turbo -t 20
```

### Run an Experiment

Create a YAML specification for reproducible experiments:

```yaml
# experiment.yaml
conversations:
  - agent_a: claude-3-haiku
    agent_b: gpt-4o-mini
    initial_prompt: "What is consciousness?"
    turns: 20
    temperature_a: 0.7
    temperature_b: 0.9
```

Run it:

```bash
pidgin experiment run experiment.yaml
```

## Monitoring Long Conversations

For conversations over 50 turns, use the monitor:

```bash
# In terminal 1: Run the conversation
pidgin run -a claude -b gpt -t 200 --display monitor

# In terminal 2: Watch system-wide status
pidgin monitor
```

## Quick Analysis

After running a conversation:

```bash
# See basic stats
# View experiment output
ls -la pidgin_output/experiments/cosmic-prism/

# Import to DuckDB for analysis
pidgin analyze cosmic-prism
```

This creates a Jupyter notebook with pre-loaded queries and visualizations.

## Next Steps

- **Explore display modes**: Try `--display chat` for full messages
- **Run experiments**: Create YAML files for batch conversations
- **Branch conversations**: Use `pidgin branch` to explore alternate paths
- **Analyze patterns**: Use the generated Jupyter notebooks

## Tips

1. **Start small**: Use 5-10 turns while learning
2. **Use cheap models**: Haiku and GPT-4o-mini for experimentation
3. **Save money**: Set temperature to 0 for deterministic outputs
4. **Monitor costs**: Check token usage in the progress panel

## Getting Help

```bash
# General help
pidgin --help

# Command-specific help
pidgin run --help

# List all commands
pidgin --help
```

See the [CLI Usage Guide](cli-usage.md) for comprehensive documentation.