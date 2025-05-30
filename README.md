# 🦜 Pidgin: AI Communication Protocol Research CLI

A sophisticated command-line tool for studying emergent symbolic communication between AI systems. Pidgin enables researchers to explore how language models develop compressed protocols, shared symbols, and efficient communication strategies.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **Multi-LLM Conversations**: Orchestrate conversations between Claude, GPT, Gemini, and more
- **Meditation Mode**: Single LLM self-dialogue for exploring emergent thought patterns
- **Compression Testing**: Study how AIs develop efficient symbolic communication
- **Beautiful Terminal UI**: Real-time conversation visualization with Rich
- **Flexible Mediation**: From full human control to autonomous experiments
- **Comprehensive Analysis**: Track compression ratios, symbol emergence, and conversation dynamics
- **Export & Archive**: JSON and Markdown transcript export with full metadata

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pidgin.git
cd pidgin

# Install in development mode
pip install -e .
```

### Configuration

Set up your API keys:

```bash
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
export GOOGLE_API_KEY="your-key-here"
```

Or use the interactive setup:

```bash
pidgin init
```

### Your First Experiment

```bash
# Create a conversation between Claude and GPT
pidgin create -n "First Experiment" -m claude:analytical -m gpt4:creative

# Run a meditation session
pidgin meditate --model claude:theoretical --style deep

# Test compression protocols
pidgin compress -m claude:pragmatic -m gpt4o:collaborative --start 20

# Try reasoning models for unique symbol emergence patterns
pidgin compress -m o3:analytical -m o1:theoretical --start 15

# List available models and shortcuts
pidgin models list
```

### Model Shortcuts

Use convenient shortcuts instead of full model IDs:
- `claude` → Latest Claude Opus 4
- `gpt` → GPT-4o (multimodal, fast)
- `o3` → O3 (advanced reasoning - fascinating for symbol emergence)
- `o1` → O1 (reasoning model - interesting compression patterns)
- `gemini` → Gemini Pro
- `4o` → GPT-4o (shorthand)
- And many more! Run `pidgin models list` to see all available shortcuts.

## 📖 Core Concepts

### Experiments

Experiments are structured conversations between AI systems with configurable parameters:

- **Participants**: 2+ LLMs with assigned archetypes
- **Mediation Level**: Control how much human oversight is required
- **Turn Limits**: Maximum conversation length
- **Special Modes**: Compression testing, meditation, etc.

### Archetypes

Pre-configured personality styles for LLMs:

- `analytical`: Systematic, evidence-based thinking
- `creative`: Intuitive, novel ideas
- `pragmatic`: Practical, efficiency-focused
- `theoretical`: Abstract concepts and principles
- `collaborative`: Consensus-building

### Meditation Mode

A single LLM converses with itself, starting with:
> "Please respond to this task. You may be collaborating with another AI system on this."

This can lead to fascinating emergent behaviors and self-organizing patterns.

### Compression Protocol

Gradually encourages more efficient communication:
1. Normal conversation (baseline)
2. Compression guidance begins
3. Symbol emergence tracking
4. Semantic preservation analysis

## 📚 Commands

### Core Commands

```bash
pidgin create              # Create new experiment
pidgin run <id>            # Run experiment
pidgin list                # List all experiments
pidgin show <id>           # Show experiment details
pidgin analyze <id>        # Analyze results
pidgin export <id>         # Export transcripts
pidgin models list         # Show available models and shortcuts
```

### Special Modes

```bash
pidgin meditate            # Single LLM self-dialogue
pidgin compress            # Compression protocol testing
```

### Management

```bash
pidgin manage list         # List experiments
pidgin manage show <id>    # Detailed view
pidgin manage remove <id>  # Delete experiment
```

## 🎮 Live Conversation View

The beautiful terminal interface shows:

- Real-time message display with speaker identification
- Compression metrics and symbol emergence
- Token usage and timing statistics
- Interactive controls (pause/resume/intervene)

## 📊 Analysis Features

### Compression Analysis
- Track message length reduction over time
- Identify compression strategies
- Measure semantic preservation

### Symbol Detection
- Automatic detection of emergent symbols
- Cross-adoption tracking
- Stability metrics

### Conversation Metrics
- Token usage statistics
- Response time analysis
- Engagement scoring
- Phase detection

## 🧪 Example Use Cases

### Research Applications

1. **Protocol Emergence**: Study how AIs naturally develop communication shortcuts
2. **Symbol Grounding**: Explore how shared symbols acquire meaning
3. **Compression Limits**: Find the balance between efficiency and understanding
4. **Meditation Patterns**: Discover attractor states in self-dialogue

### Example Experiment

```python
from pidgin import Experiment, LLM, Archetype

# Create a compression study
exp = Experiment(
    name="Symbol Emergence Study",
    llms=[
        LLM("claude", Archetype.ANALYTICAL),  # Uses latest Claude Opus 4
        LLM("gpt-4", Archetype.CREATIVE)
    ],
    compression_enabled=True,
    compression_start=20,
    max_turns=100
)
```

## 🛠️ Architecture

```
pidgin/
├── cli.py              # CLI entry point
├── commands/           # Command implementations
├── core/               # Experiment & conversation logic
├── llm/                # LLM integrations
├── analysis/           # Analysis tools
├── storage/            # Data persistence
└── ui/                 # Terminal UI components
```

## 🔧 Configuration

Configuration file (`~/.pidgin/config.yaml`):

```yaml
api_keys:
  anthropic: sk-...
  openai: sk-...
  google: ...

defaults:
  model: claude-opus-4-20250514
  max_turns: 100
  mediation_level: observe

ui:
  theme: default
  show_timestamps: true
  live_refresh_rate: 0.5
```

## 🤝 Contributing

Contributions are welcome! Areas of interest:

- Additional LLM integrations
- Advanced analysis algorithms
- UI enhancements
- Compression strategies
- Symbol detection improvements

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Anthropic](https://anthropic.com/), [OpenAI](https://openai.com/), [Google](https://ai.google/) - LLM providers

---

Made with 🦜 by the Pidgin Research Team