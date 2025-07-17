# Conversation Branching Workflow

## Overview

Branching allows you to fork an existing conversation from any turn and continue with different parameters. This is useful for:

- Testing how different temperatures affect convergence
- Swapping models mid-conversation
- Creating alternative conversation paths
- A/B testing different awareness levels

## Basic Usage

### 1. Find a conversation to branch from

First, identify the conversation you want to branch:

```bash
pidgin monitor  # Lists all experiments and conversations
```

### 2. Branch from the last turn

Create a simple branch that continues from where the conversation left off:

```bash
pidgin branch conv_exp_abc123_def456
```

### 3. Branch from a specific turn

Fork the conversation from turn 10:

```bash
pidgin branch conv_exp_abc123_def456 --turn 10
```

### 4. Change parameters

Branch with different models:

```bash
pidgin branch conv_exp_abc123_def456 -a gpt-4 -b claude
```

Branch with different temperatures:

```bash
pidgin branch conv_exp_abc123_def456 --temp-a 1.5 --temp-b 0.8
```

### 5. Create multiple branches

Run 5 branches with varied parameters:

```bash
pidgin branch conv_exp_abc123_def456 -r 5 --temperature 1.2
```

### 6. Save branch configuration

Save the branch setup as a YAML file for later reuse:

```bash
pidgin branch conv_exp_abc123_def456 --spec my_branch.yaml
```

## Advanced Usage

### Complex parameter sweeps

Create a branch that changes multiple parameters:

```bash
pidgin branch conv_exp_abc123_def456 \
  --turn 15 \
  -a claude-3-opus \
  -b gpt-4-turbo \
  --temp-a 1.8 \
  --awareness-a research \
  --max-turns 30 \
  --name "high_temp_test" \
  -r 10
```

### Using saved branch specs

Once you've saved a branch configuration, you can re-run it:

```bash
pidgin run my_branch.yaml
```

## Implementation Details

When you branch a conversation:

1. The system extracts all messages up to the specified turn
2. These messages become the "warm start" for the new conversation
3. The conversation continues with the new parameters
4. A `ConversationBranchedEvent` is emitted to track the relationship

The branched conversation inherits:
- All messages up to the branch point
- System prompts (unless overridden)
- The conversational context and history

The branched conversation can change:
- Models (agent_a, agent_b)
- Temperatures
- Awareness levels
- Maximum turns
- Any other conversation parameters

## Example Scenarios

### Scenario 1: Temperature Impact Study

You notice interesting convergence behavior at turn 20. Branch multiple times with different temperatures:

```bash
for temp in 0.5 0.8 1.0 1.2 1.5; do
  pidgin branch conv_exp_abc123 --turn 20 --temperature $temp --name "temp_${temp}_branch" -q
done
```

### Scenario 2: Model Comparison

Compare how different models would continue the same conversation:

```bash
pidgin branch conv_exp_abc123 --turn 15 -b gpt-4 --name "gpt4_branch"
pidgin branch conv_exp_abc123 --turn 15 -b claude --name "claude_branch"
pidgin branch conv_exp_abc123 --turn 15 -b gemini-pro --name "gemini_branch"
```

### Scenario 3: Awareness Level Testing

Test how different awareness levels affect the conversation trajectory:

```bash
pidgin branch conv_exp_abc123 --awareness research --name "research_aware"
pidgin branch conv_exp_abc123 --awareness none --name "no_awareness"
```

## Notes

- Branches are full experiments that can be monitored with `pidgin monitor`
- Branch names are auto-generated with "_branch" suffix if not specified
- The original conversation remains unchanged
- Branches can themselves be branched, creating conversation trees
- All branch relationships are tracked in the event log