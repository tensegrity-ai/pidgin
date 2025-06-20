# Pidgin Development Guide

## Philosophy

**We're studying patterns, not building protocols.**

Pidgin records AI conversations to see if interesting patterns are real or artifacts. That's it. No grand visions, no revolutionary claims, just careful observation and measurement.

## Code Style

### Visual Design - Nord Theme
```python
# Use Nord colors for consistency
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

### Implementation Discipline

**Follow specifications exactly.** When implementing from a prompt:

```python
# GOOD: Implement exactly what was asked
def handle_input(self, key: str):
    if key.lower() == 'd':
        self.detach()
    elif key.lower() == 's':
        self.stop_with_confirmation()
    # That's it. No extra features.

# BAD: Adding unrequested features
def handle_input(self, key: str):
    if key.lower() == 'd':
        self.detach()
    elif key.lower() == 's':
        self.stop_with_confirmation()
    elif key.lower() == 'e':  # Nobody asked for export
        self.export()
    elif key.lower() == 'p':  # Nobody asked for pause
        self.pause()
```

**Resist feature creep.** If it's not in the spec, don't add it:
- Asked for 2 commands? Don't implement 6
- Asked for simple display? Don't add animations
- Asked for data view? Don't add interpretations

### Language Discipline

**Present data, not narratives:**

```python
# GOOD: Just the facts
"Vocabulary overlap: 73%"
"Message length: 42 chars"
"Symbol usage: 8 instances"

# BAD: Interpretive language
"High convergence detected!"
"Entering compression phase"
"Gratitude spiral emerging"
```

**Use skeptical language:**
- "observed" not "discovered"
- "patterns" not "phenomena"  
- "might indicate" not "proves"
- "in our tests" not "universally"

### Code Organization

```python
# Everything emits events for observability
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

**Event-driven for complete observability:**
```
Conductor → EventBus → Components
         ↓
      events.jsonl (complete record)
```

**Provider abstraction for model flexibility:**
```python
class Provider(ABC):
    async def stream_response(messages, temperature=None):
        yield chunk
```

## What NOT to Build

1. **Intervention systems** - We observe, not manipulate
2. **Complex frameworks** - Keep it simple and debuggable
3. **"AI consciousness" features** - Stay grounded in data
4. **Protocol competitors** - MCP already exists for that

## Git Workflow

```bash
# Clear, specific commits
git commit -m "add vocabulary overlap metric"
git commit -m "fix rate limit calculation"

# Not grandiose
git commit -m "Revolutionary AI Discovery!!!"
```

## Remember

The human has been frustrated by:
- Previous implementations adding unwanted complexity
- Grandiose claims about "discoveries"
- Features that weren't requested
- Interpretive overlays on raw data

**Keep it simple. Keep it honest. Show the data.**