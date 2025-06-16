# Development Guide for Pidgin

## What This Project Actually Is

Pidgin is a well-developed research tool with ~20 modules for recording and analyzing AI conversations. We've noticed interesting behaviors but haven't proven anything statistically. The tool is feature-complete for single conversations - what's missing is batch execution and validation.

## Development Environment

### Package Management
This project uses **Poetry** for dependency management:

```bash
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Add new dependencies
poetry add package-name

# Add dev dependencies
poetry add --group dev package-name

# Run commands in virtual environment
poetry run pidgin chat -a claude -b gpt
```

### Code Style

#### Colors - Nord Theme
Use the Nord color palette for all terminal output:
```python
NORD_COLORS = {
    "nord0": "#2e3440",   # Polar Night - darkest
    "nord1": "#3b4252",   # Polar Night
    "nord2": "#434c5e",   # Polar Night
    "nord3": "#4c566a",   # Polar Night - comments/subtle
    "nord4": "#d8dee9",   # Snow Storm - main content
    "nord5": "#e5e9f0",   # Snow Storm
    "nord6": "#eceff4",   # Snow Storm - brightest
    "nord7": "#8fbcbb",   # Frost - teal
    "nord8": "#88c0d0",   # Frost - light blue
    "nord9": "#81a1c1",   # Frost - blue
    "nord10": "#5e81ac",  # Frost - dark blue
    "nord11": "#bf616a",  # Aurora - red
    "nord12": "#d08770",  # Aurora - orange
    "nord13": "#ebcb8b",  # Aurora - yellow
    "nord14": "#a3be8c",  # Aurora - green
    "nord15": "#b48ead",  # Aurora - purple
}
```

#### Glyphs Not Emoji
Use Unicode glyphs for visual elements:
```python
# Good - geometric glyphs
"◆ Starting conversation"
"▶ Continue"
"■ Stop"
"○ Pending"
"● Complete"
"⟐ Duration"

# Bad - emoji
"🚀 Starting"
"✅ Done"
"❌ Error"
```

Common glyphs:
- Shapes: ◆ ◇ ○ ● □ ■ ▲ ▼ ► ◄
- Arrows: → ← ↔ ⇒ ⇐ ⇔ ➜ 
- Math: ≈ ≡ ≠ ≤ ≥ ± × ÷
- Box: ┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼

## Current Reality

### Working ✅
- Event system records everything
- Streaming from all providers
- Ctrl+C interrupt
- Clean file output

### Partial 🚧
- Metrics calculated but not shown
- Context tracking exists but unused

### Missing ❌
- Batch experiments (critical)
- Statistical analysis
- Message injection
- Pattern validation

## Quick Start

```bash
# Run a conversation
pidgin chat -a claude -b gpt -t 20

# Check output
ls ./pidgin_output/conversations/*/
cat ./pidgin_output/conversations/*/events.jsonl
```

## Architecture That Exists

```
CLI → Conductor → EventBus → events.jsonl
         ↓
     Providers → Streaming → Display
```

Not built: batch runner, analysis tools, validation frameworks.

## Code Guidelines

### What to Build
1. Things that emit events
2. Things that analyze events
3. Things that validate observations

### What NOT to Build
- Complex frameworks
- "Revolutionary" features
- Anything claiming "proven" results

### Adding Features

```python
# Good: Observable action
await self.bus.emit(SomethingHappenedEvent(...))

# Bad: Hidden state
self.secret_state = {"dont": "do this"}
```

## Testing

```bash
pytest                          # Run all tests
pytest tests/test_conductor.py  # Single file
pytest -v --cov=pidgin         # With coverage
```

## Common Tasks

### Run Different Models
```bash
pidgin chat -a opus -b gpt-4.1 -t 30
pidgin chat -a haiku -b gemini -t 50
```

### Check Convergence (manual)
```python
# In the JSON output, look for structural patterns
# No automated tools yet - that's what we need built
```

## Priority Development Areas

### 1. Convergence Threshold System
```python
# Simple threshold-based stopping
if convergence_score >= threshold:
    stop_conversation("high_convergence")
```

Configuration:
```yaml
conversation:
  convergence_threshold: 0.85  # Stop at 85% similarity
  convergence_action: "stop"   # or "warn"
```

### 2. Batch Runner (CRITICAL)
```python
# Concept (not built):
async def run_batch(config, n=100):
    """Run n identical conversations for statistics"""
    results = []
    for i in range(n):
        conv = await run_conversation(config)
        results.append(conv)
    return analyze_patterns(results)
```

### 3. Display Convergence
```python
# Add to display_filter.py
if convergence > 0:
    console.print(f"[{NORD_COLORS['nord3']}]Convergence: {convergence:.2f}[/{NORD_COLORS['nord3']}]")
    if convergence > 0.75:
        console.print(f"[{NORD_COLORS['nord13']}]⚠ High convergence warning[/{NORD_COLORS['nord13']}]")
```

## What We've Observed (Not Proven)

- Gratitude spirals in polite models
- Possible linguistic compression
- Model-specific conversation styles
- High sensitivity to initial conditions

These need validation through batch experiments.

## Contributing

We need:
1. **Batch execution** - Run many conversations
2. **Pattern detection** - Find what we're missing  
3. **Statistical tools** - Validate observations
4. **Skeptical review** - Challenge our assumptions

## Don't Do This

- Don't claim discoveries
- Don't add philosophy  
- Don't build frameworks
- Don't compete with MCP

## Do This

- Run experiments
- Analyze data
- Question everything
- Keep it simple

## Research Ethics

- Label everything "preliminary"
- No claims without data
- Open about limitations
- Invite replication

## File Structure
```
pidgin/
├── cli.py              # Command-line interface
├── conductor.py        # Main orchestrator (~500 lines)
├── event_bus.py        # Event publish/subscribe system
├── events.py           # Event type definitions
├── event_logger.py     # Event display formatting
├── display_filter.py   # Human-readable output
│
├── providers/          # AI provider integrations
│   ├── anthropic.py    # Claude models
│   ├── openai.py       # GPT/O-series
│   ├── google.py       # Gemini models
│   └── xai.py          # Grok models
│
├── dialogue_components/# Separated display components
├── convergence.py      # Convergence calculation
│
├── config.py           # Configuration management
├── context_manager.py  # Token/context tracking
├── convergence.py      # Convergence calculator
├── dimensional_prompts.py # Prompt generation
├── intervention_handler.py # Pause/resume handling
├── metrics.py          # Turn metrics
├── models.py           # Model configurations
├── router.py           # Message routing
├── system_prompts.py   # System prompt templates
├── transcripts.py      # Transcript generation
├── types.py            # Type definitions
└── user_interaction.py # User interaction

./pidgin_output/        # All output here
└── conversations/      # Organized by date
```

## Commit Style

```bash
# Lowercase, pragmatic
git commit -m "add batch runner skeleton"
git commit -m "fix convergence display"

# Not
git commit -m "Revolutionize AI Communication"
```

## Remember

1. We built a tool that works
2. We saw interesting patterns
3. We haven't proven anything
4. Statistical validation is the next step

The interesting part isn't what we've built - it's what we might learn from it. But learning requires rigorous experiments we haven't run yet.

Help us find out what's real.