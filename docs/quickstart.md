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

With API keys configured:

```bash
pidgin run -a haiku -b gpt-4o-mini -t 10 \
  -p "Let's explore the concept of emergence in complex systems"
```

**What's happening:**
- `-a haiku`: Agent A uses Claude Haiku
- `-b gpt-4o-mini`: Agent B uses GPT-4o Mini
- `-t 10`: Run for 10 turns
- `-p "..."`: Initial prompt to start the conversation

### 3. Watch the Output

By default, Pidgin shows a chat display with message bubbles, turn separators, and convergence tracking.

Other display modes:

```bash
# Raw event stream
pidgin run -a haiku -b gpt-4o-mini -t 10 --tail

# Run in background
pidgin run -a haiku -b gpt-4o-mini -t 10 -q
```

## Understanding Output Files

After running, find your results in `pidgin_output/`:

```
pidgin_output/
  experiments/
    cosmic-prism_a1b2c3d4/
      manifest.json            # Experiment metadata and state
      events_conv_xxx.jsonl    # All events for conversation
      transcript_summary.md    # Readable transcript
  experiments.duckdb           # Analytics database (auto-imported)
```

### View the Events

```bash
# Follow live events
tail -f pidgin_output/experiments/cosmic-prism_*/events_*.jsonl

# Count events by type
cat pidgin_output/experiments/cosmic-prism_*/events_*.jsonl | \
  jq -r '.event_type' | sort | uniq -c

# Extract just the messages
cat pidgin_output/experiments/cosmic-prism_*/events_*.jsonl | \
  jq -r 'select(.event_type == "MessageCompleteEvent") | .message.content'
```

## Common Workflows

### Context Window Management

By default, conversations end naturally when context limits are reached:

```bash
# Default: conversation ends at context limit
pidgin run -a haiku -b gpt-4o-mini -t 100

# Enable truncation for very long conversations
pidgin run -a haiku -b gpt-4o-mini -t 100 --allow-truncation
```

### Run an Experiment

For batch conversations, use YAML specs or the `-r` flag:

```bash
# Quick: multiple repetitions
pidgin run -a sonnet -b gpt-4o -r 10 --name my_experiment

# From YAML spec
pidgin run experiment.yaml
```

### Monitor Long Experiments

```bash
# In terminal 1: run the experiment
pidgin run -a opus -b gpt-4o -r 20 --name long_study

# In terminal 2: watch system-wide status
pidgin monitor
```

## Tips

1. **Start small**: Use 5-10 turns while learning
2. **Use cheap models**: Haiku and GPT-4o-mini for experimentation
3. **Monitor costs**: Check token usage in the chat display
4. **Save specs**: Use YAML files for reproducibility

## Getting Help

```bash
pidgin --help
pidgin run --help
pidgin models
```

See the [CLI Usage Guide](cli-usage.md) for comprehensive documentation.
