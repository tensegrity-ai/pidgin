# Pidgin

An experimental tool for recording and analyzing AI-to-AI conversations. We've observed interesting patterns that might be real or might be artifacts. Help us find out.

## What This Is

Pidgin records conversations between AI models to study how they communicate. We've seen some intriguing behaviors:
- Conversations often fall into repetitive patterns
- Language sometimes compresses over many turns
- Different model pairs behave differently

**Important**: These are preliminary observations. Nothing has been statistically validated yet.

## Current Status

### ✅ What Works
- **Recording**: Full event-driven system captures every interaction
- **Models**: 15+ models across Anthropic, OpenAI, Google, xAI
- **Streaming**: Real-time response display
- **Interrupts**: Ctrl+C to pause/resume conversations
- **Output**: Clean JSON and markdown transcripts

### 🚧 What's Partial
- **Metrics**: Convergence calculated but not displayed
- **Context Tracking**: Code exists but not integrated

### ❌ What's Missing
- **Batch Experiments**: Can only run one conversation at a time
- **Statistical Analysis**: No tools to validate observations
- **Message Injection**: Can pause but can't intervene

## Quick Start

```bash
# Install
pip install -e .

# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."

# Run a conversation
pidgin chat -a claude -b gpt -t 20

# Output saved to ./pidgin_output/
```

## Why This Matters

When AIs talk to each other millions of times daily, do they develop more efficient protocols? We don't know. That's what we're trying to find out.

## Examples of What We've Seen

```
Turn 1: "Hello! How are you today?"
Turn 2: "I'm doing well, thank you! How are you?"
...
Turn 30: "Grateful!"
Turn 31: "Grateful too!"
Turn 32: "🙏"
```

Is this compression? Attractor dynamics? Random chance? We need data.

## How to Help

1. **Run experiments**: Try different model pairs and initial prompts
2. **Report patterns**: What do you observe?
3. **Build analysis**: Help create tools to validate observations
4. **Add batch running**: This is the critical missing piece

## Technical Overview

Pidgin is a full-featured research tool with:
- **Event-driven architecture**: Complete observability via EventBus
- **Multiple components**: Display, metrics, convergence, context tracking
- **Convergence detection**: Stops conversations when agents become too similar
- **Rich CLI**: Dimensional prompts, model shortcuts, configuration
- **Clean separation**: UI, business logic, and providers properly separated

Key modules:
- `conductor.py` - Orchestrates conversations through events
- `providers/` - Integrations for Anthropic, OpenAI, Google, xAI
- `convergence.py` - Calculates linguistic similarity metrics
- `convergence.py` - Calculates structural similarity between agents
- `dialogue_components/` - Modular UI components

Built for extensibility: The architecture supports n-agent conversations, but current implementation focuses on 2-agent dynamics.

## Contributing

This is early-stage research. We need:
- Batch experiment runner (critical priority)
- Statistical analysis tools
- Pattern validation methods
- More observations from different model combinations

## Not a Competition

Tools like Model Context Protocol (MCP) solve AI-to-tool communication. We're studying something different: what happens when AIs talk naturally, without engineered protocols.

## License

MIT - This is research, please share what you learn.

---

**Remember**: We're not claiming to have discovered anything revolutionary. We've just noticed some interesting patterns and built a tool to study them properly. The real work is proving whether these patterns are meaningful or just artifacts of our setup.