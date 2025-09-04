---
layout: default
title: Home
---

# Pidgin: AI Linguistic Observatory

An experimental tool for recording and analyzing AI-to-AI conversations. We've observed interesting patterns that might be real or might be artifacts. Help us find out.

## What This Is

Pidgin records conversations between AI models to study how they communicate. We've seen some intriguing behaviors:

- Conversations often fall into repetitive patterns
- Language sometimes compresses over many turns  
- Different model pairs behave differently

**Important**: These are preliminary observations. Nothing has been statistically validated yet.

## Quick Example

```bash
# Install
uv tool install pidgin-ai

# Run a conversation
pidgin run -a claude -b gpt-4 -t 20

# Watch it happen
pidgin run -a claude -b gpt-4 --verbose
```

## Examples of What We've Seen

```
Turn 1: "Hello! How are you today?"
Turn 2: "I'm doing well, thank you! How are you?"
...
Turn 30: "Grateful!"
Turn 31: "Grateful too!"
Turn 32: "◆"
```

Is this convergence meaningful or just a quirk? That's what we're trying to understand.

## Documentation

### Getting Started
- **[Installation Guide](installation.md)** - Install Pidgin with pip, Poetry, or from source
- **[Quickstart Tutorial](quickstart.md)** - Run your first conversation in 5 minutes
- **[CLI Reference](cli-usage.md)** - Complete command-line interface documentation

### User Guides
- **[YAML Specifications](yaml-specs.md)** - Configure experiments with YAML files
- **[Custom Awareness](custom-awareness.md)** - Control agent awareness and context
- **[Branching Workflow](branching_workflow.md)** - Explore alternate conversation paths

### Architecture & Analysis
- **[Database Schema](database.md)** - DuckDB schema and query examples
- **[Metrics Reference](metrics.md)** - All 150+ metrics explained
- **[Conversation Architecture](conversation-architecture.md)** - System design and event flow

### API Documentation
- **[Core API](api/core.md)** - Conductor, agents, and conversations
- **[Providers API](api/providers.md)** - Model providers and customization

## Features

### ✅ What Works
- **Recording**: JSONL-based event capture for every interaction
- **Models**: 20+ models across Anthropic, OpenAI, Google, xAI, and local (Ollama)
- **Analysis**: 150+ metrics per turn in DuckDB wide-table format
- **Monitoring**: Live system monitor and standard Unix tools (tail, grep, jq)
- **Notebooks**: Auto-generated Jupyter notebooks for each experiment
- **Branching**: Create alternate conversation paths from any turn

### ⚠️ What's Partial
- **Advanced Metrics**: Placeholder columns for semantic similarity (calculate post-hoc)
- **Statistical Validation**: Basic analysis works, significance testing coming

### ❌ What's Missing
- **Multi-modal Support**: Text-only for now
- **Multi-party**: Conversations limited to two participants

## Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/tensegrity-ai/pidgin/blob/main/CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](https://github.com/tensegrity-ai/pidgin/blob/main/LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/tensegrity-ai/pidgin)
- [Issue Tracker](https://github.com/tensegrity-ai/pidgin/issues)
- [Changelog](https://github.com/tensegrity-ai/pidgin/blob/main/CHANGELOG.md)