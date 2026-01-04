# Extended Thinking

Extended thinking allows Claude models to expose their internal reasoning process before generating a response. This is useful for understanding how models approach complex problems and for debugging unexpected behavior.

## Overview

When extended thinking is enabled, Claude models generate a "thinking" phase before their actual response. This reasoning trace shows the model's step-by-step thought process, including:

- Problem decomposition
- Consideration of alternatives
- Self-correction and refinement
- Planning before response generation

The thinking content is captured separately from the response and can be viewed in real-time during chat or queried from the database after experiments.

## CLI Options

### Enable Thinking

```bash
# Enable for both agents
pidgin run -a claude -b claude --think

# Enable for specific agent only
pidgin run -a claude -b gpt --think-a
pidgin run -a gpt -b claude --think-b
```

### Thinking Budget

Control the maximum tokens allocated to the thinking phase:

```bash
# Default budget is 10,000 tokens
pidgin run -a claude -b claude --think

# Custom budget (range: 1,000 - 100,000)
pidgin run -a claude -b claude --think --thinking-budget 5000
pidgin run -a claude -b claude --think --thinking-budget 50000
```

Higher budgets allow more extensive reasoning but increase token costs and response time.

## Provider Support

| Provider | Support | Notes |
|----------|---------|-------|
| Anthropic (Claude) | Full | Native API support via `thinking` block |
| OpenAI | None | Parameters accepted but ignored |
| Google | None | Parameters accepted but ignored |
| xAI | None | Parameters accepted but ignored |
| Ollama | None | Not supported |
| Local (test) | None | Not supported |

## Constraints

When extended thinking is enabled:

1. **Temperature is forced to 1.0** - The API requires temperature=1.0 for thinking mode
2. **Only Claude 3.5+ models** - Earlier models do not support extended thinking
3. **Increased max tokens** - Response limit increases to 16,000 tokens (vs 1,000 default)
4. **Higher latency** - Thinking phase adds to response time

## Examples

### Basic Chat with Thinking

```bash
# Interactive chat with thinking enabled
pidgin chat -a claude --think

# The thinking trace appears in a collapsible panel before the response
```

### Experiment with Thinking

```bash
# Run an experiment with thinking for analysis
pidgin run -a claude -b claude --think -t 10 -n thinking_experiment
```

### Mixed Configuration

```bash
# Only one agent uses thinking
pidgin run -a claude -b gpt --think-a -t 20

# Different budgets per agent (via YAML spec)
```

### YAML Specification

```yaml
agent_a: claude
agent_b: claude
turns: 10
thinking_enabled_a: true
thinking_enabled_b: true
thinking_budget: 20000
```

## Viewing Thinking Traces

### During Chat

In chat mode, thinking traces are displayed in a collapsible panel above the response. The panel shows the full reasoning process with token count and duration.

### In JSONL Events

Thinking traces are captured as `ThinkingCompleteEvent` in the JSONL event stream:

```json
{
  "type": "ThinkingCompleteEvent",
  "conversation_id": "abc123",
  "turn_number": 1,
  "agent_id": "agent_a",
  "thinking_content": "Let me analyze this problem...",
  "thinking_tokens": 1523,
  "duration_ms": 4200
}
```

### Database Queries

After experiments complete, thinking traces are imported to DuckDB:

```sql
-- Get all thinking traces for a conversation
SELECT agent_id, turn_number, thinking_content, thinking_tokens
FROM thinking_traces
WHERE conversation_id = 'your_conversation_id'
ORDER BY turn_number;

-- Aggregate thinking statistics
SELECT
  agent_id,
  COUNT(*) as trace_count,
  SUM(thinking_tokens) as total_tokens,
  AVG(thinking_tokens) as avg_tokens
FROM thinking_traces
WHERE experiment_id = 'your_experiment_id'
GROUP BY agent_id;
```

## Use Cases

- **Complex reasoning tasks**: Enable thinking for problems requiring multi-step logic
- **Debugging responses**: Understand why a model gave an unexpected answer
- **Research**: Analyze how models approach different types of problems
- **Comparison**: Compare reasoning patterns between model versions

## Related Documentation

- [CLI Usage](cli-usage.md) - Full command reference
- [Database](database.md) - Querying experiment data
- [Metrics](metrics.md) - Available metrics and calculations
