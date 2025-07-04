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
         ↓         ↓
   events.jsonl   DuckDB
   (legacy)      (metrics only)
```

Everything emits events. No hidden state. Complete audit trail.

**Note**: Currently in transition - events are double-written to both jsonl files and intended for DuckDB. Priority #1 is consolidating to DuckDB only.

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

## Implementation Examples

### Desktop Notifications

When implementing desktop notifications, use these platform-specific commands:

```bash
# macOS
osascript -e 'display notification "Experiment complete" with title "Pidgin"'

# Linux  
notify-send "Pidgin" "Experiment complete"

# Terminal bell (cross-platform)
echo -e "\a"
```

### Testing Models

Always use local test model to avoid API calls during development:
```bash
pidgin chat -a local:test -b local:test -t 5
```

### Database Concurrency

DuckDB uses MVCC (Multi-Version Concurrency Control) and handles locking internally:
- Multiple readers allowed simultaneously
- Only one writer at a time (blocks others)
- No configurable lock timeout

**Our approach:**
- EventStore handles retries with exponential backoff
- Lock errors retry faster (0.5-1s) than other errors  
- System monitor uses read-only connections to avoid conflicts
- No complex queue infrastructure needed - let DuckDB handle it

## Current State

The core architecture is complete and functional. We're now focused on:

1. **Data flow cleanup** - Consolidate event storage to DuckDB only (Priority #1)
2. **Analysis infrastructure** - GraphQL server and auto-generated Jupyter notebooks
3. **Pattern detection** - Gratitude spirals and other research features
4. **Performance optimization** - Once data flow is clean

## Note on TODOs

All project TODOs are tracked in TODO.md. This file focuses on development guidelines and philosophy.