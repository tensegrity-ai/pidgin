# Development Guidelines for Pidgin

These guidelines ensure consistent, grounded development of the Pidgin research tool.

## Core Philosophy

### 1. Scientific Rigor Over Hype
- **Observe**, don't interpret
- **Record**, don't theorize  
- **Measure**, don't speculate
- **Question**, don't assume

### 2. Build Only What's Needed
- If it's not in the spec, don't add it
- Asked for 2 commands? Don't implement 6
- Asked for simple display? Don't add animations
- Asked for data view? Don't add interpretations

### 3. Language Discipline

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

## Architecture Principles

### Event-Driven for Complete Observability
```
Conductor → EventBus → Components
         ↓
      events.jsonl (complete record)
```

Everything emits events. No hidden state. Complete audit trail.

### Provider Abstraction for Model Flexibility
```python
class Provider(ABC):
    async def stream_response(messages, temperature=None):
        yield chunk
```

Clean boundaries. Easy to add providers. No model-specific logic in core.

### Database Design for Analysis
- DuckDB for analytical workloads
- Single file, zero configuration
- Columnar storage for metrics
- Optimized for research queries

## Code Standards

### Module Organization
```python
# Small, focused modules
# <200 lines per file
# Single responsibility
# Clear interfaces
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

### Event Emission
```python
# Everything significant emits an event
await self.bus.emit(TurnCompleteEvent(...))

# No direct coupling between components
# Components subscribe to events they care about
```

## What NOT to Build

1. **Real-time dashboards** - Static analysis is sufficient
2. **Complex visualizations** - Let researchers use their own tools
3. **AI consciousness features** - Stay grounded in data
4. **Protocol engineering** - We observe, not design
5. **Intervention systems** - We record, not manipulate

## CLI Design

### Commands Should Be:
- **Obvious**: `pidgin chat`, not `pidgin converse`
- **Consistent**: Always `--agent-a`, never mix with `--model-1`
- **Documented**: Help text for everything
- **Stateless**: No hidden config files changing behavior

### Status Over Live Updates
```bash
# GOOD: Clear status on demand
pidgin experiment status my_experiment

# BAD: Complex live dashboard
pidgin experiment monitor --live --refresh-rate 2
```

## Experiment Design

### Sequential by Default
- Rate limits are real
- Hardware constraints exist
- Parallel architecture exists but rarely used
- Document reality, not theory

### Metrics Are Raw Data
- Calculate everything
- Interpret nothing
- Store all metrics
- Let researchers analyze

## Git Workflow

```bash
# Clear, specific commits
git commit -m "add vocabulary overlap metric"
git commit -m "fix rate limit calculation"
git commit -m "switch to DuckDB for analytics"

# Not grandiose
git commit -m "Revolutionary AI Discovery!!!"
```

## Documentation Standards

### Be Honest About:
- What works (fully tested features)
- What's partial (work in progress)
- What's missing (not implemented)
- What's observed (not proven)

### Avoid:
- Marketing language
- Unfounded claims
- Feature creep in docs
- Promising future features

## Analysis Philosophy

### Data First
1. Collect comprehensive metrics
2. Store in queryable format
3. Provide export capabilities
4. Let researchers draw conclusions

### Tools Not Conclusions
- Auto-generate Jupyter notebooks
- Provide data access APIs
- Enable flexible querying
- Don't interpret results

## Remember

The human has been frustrated by:
- Previous implementations adding unwanted complexity
- Grandiose claims about "discoveries"
- Features that weren't requested
- Interpretive overlays on raw data
- Complex real-time systems that don't add value

**Keep it simple. Keep it honest. Show the data.**

## Current Focus

1. **Remove complexity** (dashboard, SharedState)
2. **Solid fundamentals** (status command, notifications)
3. **Better analysis** (DuckDB, GraphQL, Jupyter)
4. **Clean architecture** (no unnecessary abstractions)