# Pidgin

AI conversation research tool for studying emergent communication between language models.

## Overview

Pidgin enables conversations between AI agents to study how they develop compressed communication protocols and emergent symbols. It features automatic detection of conversation attractors (repetitive patterns), pause/resume functionality, and comprehensive model support for both Anthropic and OpenAI.

## Installation

### Prerequisites

- Python 3.8 or higher
- API keys for the providers you want to use:
  - Anthropic API key (for Claude models)
  - OpenAI API key (for GPT models)

### Install from source

```bash
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin
pip install -e .
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Add your API keys to the `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Or set them as environment variables:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

## Quick Start

### Basic Conversations

```bash
# Basic conversation (10 turns)
pidgin chat -a claude -b gpt -t 10

# Custom initial prompt
pidgin chat -a opus -b gpt-4.1 -t 20 -p "Let's discuss compression algorithms"

# With attractor detection disabled (for baseline experiments)
pidgin chat -a haiku -b nano -t 100 --no-attractor-detection

# Disable token warnings (for cleaner transcripts)
pidgin chat -a claude -b gpt -t 50 --no-token-warnings

# Using custom configuration
pidgin chat -a claude -b claude -t 50 --config unattended.yaml
```

### List Available Models

```bash
# List all models and their shortcuts
pidgin models

# Show detailed model information
pidgin models --detailed

# Filter by provider
pidgin models --provider anthropic
```

### Pause and Resume Conversations

```bash
# Start a long conversation
pidgin chat -a opus -b gpt-4.1 -t 500

# Press Ctrl+C to pause gracefully
# The system will save a checkpoint and show resume instructions

# Resume from the latest checkpoint
pidgin resume --latest

# Resume from specific checkpoint
pidgin resume path/to/conversation.checkpoint

# List available checkpoints
pidgin resume
```

### Available Models

Use `pidgin models` to see all available models. Key shortcuts include:

**Claude models:**
- `claude` → claude-4-sonnet-20250514 (default)
- `opus` → claude-4-opus-20250514 (most capable)
- `sonnet` → claude-4-sonnet-20250514 (balanced)
- `haiku` → claude-3-5-haiku-20241022 (fastest)

**OpenAI models:**
- `gpt` → gpt-4.1-mini (default)
- `4.1` → gpt-4.1 (flagship)
- `nano` → gpt-4.1-nano (fastest)
- `o3` → o3-mini (reasoning)
- `o4` → o4-mini (latest reasoning)

## Configuration

### Quick Start Configuration

For long research conversations, create `~/.config/pidgin.yaml`:

```yaml
# Allow very long conversations
context_management:
  warning_threshold: 85    # Warn at 85% context full
  auto_pause_threshold: 95 # Pause at 95% context full

conversation:
  attractor_detection:
    on_detection: "log"    # Don't stop on patterns
```

### Configuration Files

- `pidgin.yaml.default` - Full configuration with all options documented

Configuration is loaded from (first found):
1. `~/.config/pidgin/pidgin.yaml`
2. `~/.config/pidgin.yaml` (recommended)
3. `~/.pidgin.yaml`
4. `./pidgin.yaml` (current directory)
5. `./.pidgin.yaml`

## Output

Conversations are saved to `~/.pidgin_data/transcripts/YYYY-MM-DD/[conversation-id]/`:
- `conversation.json` - Machine-readable format with full message history and metrics
- `conversation.md` - Human-readable markdown transcript
- `conversation.checkpoint` - Resumable state (if paused)
- `attractor_analysis.json` - Attractor detection analysis (if triggered)

## Understanding Limits

### Two Types of Limits

1. **Context Window Limits** (Primary concern)
   - Total conversation size vs model's context window
   - Claude: 200,000 tokens, GPT-4: 128,000 tokens
   - This is what usually stops long conversations
   - Displayed as: `Context: 45,231/200,000 tokens (22.6%)`

2. **Rate Limits** (Secondary concern)
   - Tokens per minute (e.g., 40,000/min for Claude)
   - Only matters for rapid exchanges
   - Displayed as: `Rate: 85%/min` (only when high)
   - Usually not a problem for research conversations

### Default Behavior

- **Warnings** appear at 80% context usage
- **Auto-pause** at 90% context usage
- Rate limits only trigger warnings at 90%+ usage
- Conversations prioritize context limits over rate limits

## Key Features

### Conversation Control
- **Pause/Resume**: Press Ctrl+C to pause any conversation and resume later
- **Checkpointing**: Automatic state saving for long-running experiments
- **Graceful Interruption**: Never lose conversation progress

### Attractor Detection
- **Structural Analysis**: Identifies when conversations fall into repetitive structural patterns
- **Real-time Detection**: Shows checking indicators and status during conversations
- **Multiple Pattern Types**: Party attractors, alternating patterns, compression attractors
- **Configurable Actions**: Stop, pause, or log when attractors are detected
- **Research Metrics**: Detailed analysis of pattern formation with early detection

### Token Management
- **Predictive Warnings**: Shows remaining exchanges before hitting limits
- **Auto-Pause**: Automatically saves checkpoint when limits are imminent
- **Token Metrics**: Displays usage in conversation (can be disabled)
- **Growth Detection**: Identifies compression/expansion patterns

### Context Window Management
- **Context Tracking**: Monitors total conversation size vs model limits
- **Progressive Warnings**: Shows when approaching context window capacity
- **Auto-Pause on Limits**: Prevents crashes when context is nearly full
- **Model-Specific Limits**: Tracks different limits for Claude (200k) vs GPT (128k)
- **Usage Display**: Shows context usage alongside token metrics

### Model Support
- **15+ Models**: Full support for latest Claude and OpenAI models
- **Cross-Provider**: Mix models from different providers (Claude ↔ GPT)
- **Model Discovery**: `pidgin models` command to explore available options
- **Smart Shortcuts**: Convenient aliases like `haiku`, `gpt`, `opus`

### Configuration
- **YAML Config Files**: Customize behavior for different experiments
- **Experiment Profiles**: Pre-configured settings for common research scenarios
- **Runtime Overrides**: CLI flags for quick adjustments

### Research Features
- **Context Management**: Prevents context window crashes with predictive warnings
- **Unattended Operation**: Run thousands of experiments automatically
- **Attractor Analysis**: Understand how and when conversations fall into patterns
- **Transcript Management**: Organized storage with JSON and Markdown formats
- **Extensible Detection**: Easy to add new pattern detectors

## Research Examples

### Large-Scale Attractor Mapping
```bash
# Run 100 conversations with aggressive attractor detection
for i in {1..100}; do
  pidgin chat -a claude -b claude -t 1000 --config unattended.yaml
done
```

### Cross-Model Dynamics Study
```bash
# Test different model combinations
pidgin chat -a haiku -b gpt-nano -t 100  # Fast models
pidgin chat -a opus -b gpt-4.1 -t 100    # Capable models
pidgin chat -a claude -b o4-mini -t 100  # Mixed reasoning
```

### Baseline Experiments
```bash
# Run without attractor detection to see natural progression
pidgin chat -a claude -b claude -t 500 --no-attractor-detection
```

## Project Structure

```
pidgin/
├── pidgin/
│   ├── attractors/         # Attractor detection system
│   │   ├── manager.py      # Detection orchestration
│   │   ├── patterns.py     # Pattern definitions
│   │   └── structural.py   # Structural analysis
│   ├── providers/          # LLM provider implementations
│   ├── checkpoint.py       # Pause/resume functionality
│   ├── config_manager.py   # YAML config management
│   ├── context_manager.py  # Context window tracking
│   ├── conductor.py        # Human intervention modes
│   ├── convergence.py      # Convergence detection
│   ├── dialogue.py         # Core conversation engine
│   ├── models.py           # Model definitions and metadata
│   ├── router.py           # Message routing
│   ├── transcripts.py      # Transcript management
│   └── cli.py              # Command-line interface
├── tests/                  # Test suite
├── docs/                   # Documentation
├── pidgin.yaml.default     # Default configuration
└── README.md               # This file
```

## Development

### Setting up development environment

```bash
# Clone the repository
git clone https://github.com/yourusername/pidgin.git
cd pidgin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pidgin

# Run specific test file
pytest tests/test_core.py
```

### Code formatting and linting

```bash
# Format code
black pidgin tests

# Sort imports
isort pidgin tests

# Lint code
flake8 pidgin tests

# Type checking
mypy pidgin
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with the amazing Rich library for beautiful terminal output
- Inspired by research in emergent communication and language evolution
- Thanks to all contributors and the open-source community