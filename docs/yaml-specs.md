# Running Experiments from YAML Specifications

Pidgin supports running experiments from YAML specification files, providing a convenient way to define and share experiment configurations.

## Quick Start

```bash
pidgin run experiment.yaml
```

## Minimal Example

```yaml
# minimal.yaml
agent_a: claude
agent_b: gpt-4
prompt: "Hello, let's discuss AI safety"
```

## Field Reference

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `agent_a` or `agent_a_model` | Yes | string | - | First agent model ID |
| `agent_b` or `agent_b_model` | Yes | string | - | Second agent model ID |
| `name` | No | string | auto-generated | Experiment name |
| `prompt` or `custom_prompt` | No | string | "Hello" | Initial conversation prompt |
| `max_turns` or `turns` | No | int | 20 | Maximum conversation turns |
| `repetitions` | No | int | 1 | Number of conversations to run |
| `temperature` | No | float | model default | Temperature for both agents |
| `temperature_a` | No | float | model default | Temperature for agent A |
| `temperature_b` | No | float | model default | Temperature for agent B |
| `convergence_threshold` | No | float | 0.85 | Convergence detection threshold |
| `convergence_action` | No | string | "stop" | Action on convergence: notify, pause, stop |
| `convergence_profile` | No | string | "balanced" | Convergence weights: balanced, structural, semantic, strict |
| `awareness` | No | string | "basic" | Awareness level: none, basic, firm, research |
| `awareness_a` | No | string | - | Override awareness for agent A |
| `awareness_b` | No | string | - | Override awareness for agent B |
| `max_parallel` | No | int | 1 | Number of parallel conversations |
| `choose_names` | No | bool | false | Let agents choose their own names |
| `prompt_tag` | No | string | "[HUMAN]" | Tag to prefix initial prompt |
| `allow_truncation` | No | bool | false | Allow messages to be truncated to fit context windows |
| `output` | No | string | - | Custom output directory |

## Complete Example

```yaml
# Full example showing all available options
name: "consciousness-debate"
agent_a: claude-3-opus
agent_b: gpt-4
max_turns: 50
repetitions: 10
prompt: "What is the nature of consciousness and subjective experience?"
temperature_a: 0.7
temperature_b: 0.9
convergence_threshold: 0.85
convergence_action: stop
convergence_profile: balanced
awareness: basic
max_parallel: 5
prompt_tag: "[RESEARCHER]"
allow_truncation: false
```

## Tips

1. **Model Names**: Use the same model IDs as the CLI (e.g., `claude`, `gpt-4`, `gemini-1.5-pro`)
2. **Paths**: YAML files can be anywhere - Pidgin will load them from the specified path
3. **Comments**: Use `#` for comments to document your experiments
4. **Sharing**: YAML specs make it easy to share experiment configurations with others