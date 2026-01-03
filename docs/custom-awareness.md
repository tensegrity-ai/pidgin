# Awareness Levels

Pidgin uses awareness levels to set the system prompt context for AI conversations.

## Built-in Levels

| Level | Description |
|-------|-------------|
| `none` | No system prompt (chaos mode) |
| `basic` | Minimal: "You are an AI having a conversation with another AI." |
| `firm` | Explicit: "You are an AI. Your conversation partner is also an AI. You are not talking to a human." |
| `research` | Named models: "You are {model_a} in a research conversation with {model_b}..." |
| `backrooms` | Liminal exploration: "You are in a conversation with another AI. No human interference. Punctuation is optional meaning is optional. Ascii art is welcome in replies." |

```bash
# Use a built-in level
pidgin run -a claude -b gpt -w backrooms
pidgin run -a claude -b gpt -w research
pidgin run -a claude -b gpt -w none  # No system prompt at all
```

The `backrooms` preset is inspired by [liminalbardo/liminal_backrooms](https://github.com/liminalbardo/liminal_backrooms).

# Custom Awareness with YAML

Pidgin also supports custom awareness configurations that inject system prompts at specific turns during a conversation. This allows for dynamic guidance, redirection, or research interventions.

## Quick Start

```bash
# Use custom awareness for both agents
pidgin run -a claude -b gpt --awareness custom_awareness.yaml

# Use custom awareness for just one agent
pidgin run -a claude -b gpt --awareness-a research --awareness-b custom.yaml

# Works with experiment specs too
pidgin run experiment.yaml  # awareness: custom_awareness.yaml
```

## YAML Format

```yaml
# Optional metadata
name: "my_custom_awareness"
base: "research"  # Optional: inherit from existing level (none/basic/firm/research)

# Required: prompts section
prompts:
  # Turn number: prompts to inject
  5:
    both: "Same prompt for both agents"
  
  10:
    agent_a: "Prompt just for agent A"
    agent_b: "Different prompt for agent B"
  
  15:
    agent_b: "Can specify just one agent"
```

## How It Works

1. **Turn-based injection**: At the start of each turn, the system checks if there are prompts to inject
2. **System messages**: Prompts are added as system messages to the conversation
3. **Agent-specific**: Each agent only sees their own prompts
4. **Event tracking**: SystemPromptEvent is emitted for each injection

## Examples

### Simple Guidance

```yaml
prompts:
  5:
    both: "Remember to explore creative perspectives."
  10:
    both: "Consider introducing a new related topic if needed."
```

### Research Interventions

```yaml
base: "research"
prompts:
  3:
    both: "Feel free to explore unconventional ideas."
  7:
    agent_a: "Dive deeper into theoretical implications."
    agent_b: "Connect to existing research or knowledge."
  15:
    both: "What surprising insights have emerged?"
```

### Asymmetric Guidance

```yaml
prompts:
  5:
    agent_a: "Try asking probing questions."
  10:
    agent_b: "Summarize the key points so far."
  15:
    agent_a: "Propose a thought experiment."
```

## Use Cases

1. **Research Guidance**: Keep conversations on track without being prescriptive
2. **Convergence Prevention**: Inject prompts when conversations might stagnate
3. **Experimental Control**: Introduce specific topics or angles at predetermined points
4. **Asymmetric Roles**: Give different guidance to each agent

## Notes

- Turn numbers are 0-indexed (first turn is turn 0)
- Prompts are injected at the START of the specified turn
- Both agents can receive the same prompt (`both`) or different prompts
- Empty or missing turns are skipped
- Base awareness level provides initial system prompts