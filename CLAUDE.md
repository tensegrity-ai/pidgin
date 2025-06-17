# Pidgin Development Guide

## Quick Start

```bash
# Install
poetry install

# Run conversation
poetry run pidgin chat -a claude -b gpt -t 20

# Run experiment (batch)
poetry run pidgin experiment start -a claude -b gpt --reps 100

# View dashboard
poetry run pidgin experiment dashboard my_experiment
```

## Code Style

### Visual Design - Nord Theme
```python
# Use Nord colors for all terminal output
NORD_COLORS = {
    "dim": "#4c566a",     # nord3 - subtle text
    "text": "#d8dee9",    # nord4 - main content  
    "cyan": "#88c0d0",    # nord8 - info
    "red": "#bf616a",     # nord11 - errors
    "yellow": "#ebcb8b",  # nord13 - warnings
    "green": "#a3be8c",   # nord14 - success
    "blue": "#5e81ac",    # nord10 - primary
}

# Use geometric glyphs, not emoji
"◆ Starting"  # Good
"🚀 Starting" # Bad

# Common glyphs
◆ ◇ ○ ● □ ■ ▲ ▼ ► ◄ → ← ↔ ≈ ≡
```

### Code Organization

```python
# Everything emits events
await self.bus.emit(TurnCompleteEvent(...))

# No hidden state
# Bad: self.convergence = 0.8
# Good: emit convergence in event

# Small focused modules
# <200 lines per file
# Single responsibility
```

### Error Handling

```python
# Be specific about errors
raise ValueError(f"Model {model} not in MODELS")

# Don't hide failures
try:
    result = await api_call()
except RateLimitError as e:
    # Log it, show it, handle it
    await self.bus.emit(APIErrorEvent(...))
    raise
```

## Architecture Patterns

### Event-Driven Everything
```python
# Conductor orchestrates via events
# Components subscribe to what they need
# No direct coupling between components

# Good: Event flows
Conductor → EventBus → Component
         ↓
      events.jsonl

# Bad: Direct calls
Conductor → Component → Another Component
```

### Provider Pattern
```python
# All providers implement same interface
class Provider(ABC):
    async def stream_response(messages, temperature=None):
        yield chunk

# Wrapped with event awareness
EventAwareProvider(base_provider, event_bus)
```

## Database Schema

### Key Tables
- `experiments` - Metadata and configuration
- `conversations` - Status, models, parameters
- `turns` - ~150 metrics per turn
- `word_frequencies` - Temporal word tracking

### Metrics Captured
- Lexical: TTR, vocabulary overlap, entropy
- Structural: Message length, sentence patterns
- Behavioral: Hedge words, symbols, repetition
- Everything is 0-indexed

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pidgin

# Run specific test
pytest tests/test_experiments.py::test_batch_runner
```

### Test Philosophy
- Smoke tests over unit tests
- Test the full flow, not every function
- Mock providers for deterministic tests
- Use real providers for integration tests

## Common Tasks

### Add New Model
```python
# In config/models.py
MODELS["new-model-id"] = ModelConfig(
    model_id="new-model-id",
    shortname="NewModel",
    aliases=["new", "nm"],
    provider="openai",  # or anthropic, google, xai
    context_window=128000,
    # ... other config
)
```

### Add New Metric
1. Add to database schema
2. Add calculation in metrics module
3. Add to dashboard display
4. Emit in TurnCompleteEvent

### Debug Event Flow
```bash
# Check events.jsonl
tail -f ./pidgin_output/conversations/*/events.jsonl | jq

# Or use verbose mode
pidgin chat -a claude -b gpt -v
```

## Performance

### Targets
- Conversation start: <1s
- Message streaming: <100ms latency
- Dashboard update: <50ms
- Batch runner: 10+ conversations parallel

### Bottlenecks
- Rate limits (automatic backoff)
- Database writes (batched)
- Terminal rendering (use Rich's Live)

## Git Workflow

```bash
# Feature branches
git checkout -b add-metric-x

# Commit style (lowercase, specific)
git commit -m "add lexical diversity metric"
git commit -m "fix convergence calculation overflow"

# Not
git commit -m "Revolutionary AI Discovery!!!"
```

## What NOT to Build

1. **Intervention systems** - Distraction from research
2. **Complex frameworks** - Keep it simple
3. **"AI consciousness" features** - Stay grounded
4. **Competing protocols** - We observe, not engineer

## Debugging Tips

### Database Issues
```python
# Check schema
sqlite3 experiments.db ".schema turns"

# Query metrics
sqlite3 experiments.db "SELECT * FROM turns WHERE convergence > 0.8"
```

### Provider Issues
- Check API keys are set
- Watch for rate limits in events
- Use `--verbose` to see all events

### Display Issues
- Terminal needs Unicode support
- Minimum 120×40 for dashboard
- Use `--quiet` for minimal output

## Remember

- We're studying patterns, not building protocols
- Every claim needs data
- Simple code is debuggable code
- Events tell the whole story