# Pidgin

AI conversation research tool for studying emergent communication between language models.

## Overview

Pidgin enables conversations between AI agents (LLMs such as Claude, ChatGPT, or Gemini) to study how they develop compressed communication protocols and emergent symbols. This Phase 1 release focuses on basic AI-to-AI conversations with automatic transcript saving.

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

Run a conversation between two Claude agents:

```bash
# Basic conversation (3 turns)
pidgin chat -a claude -b claude -t 3

# Custom initial prompt
pidgin chat -a claude -b claude -t 5 -p "Let's discuss compression algorithms"

# Using specific models
pidgin chat -a opus -b sonnet -t 10

# Save to specific location
pidgin chat -a claude -b claude -t 3 -s ./my-transcripts
```

### Available Model Shortcuts

**Claude models:**
- `claude` → claude-sonnet-4-20250514
- `opus` → claude-opus-4-20250514  
- `sonnet` → claude-sonnet-4-20250514

**OpenAI models:**
- `gpt` → gpt-4.1-mini (default, fast)
- `4.1` → gpt-4.1 (flagship model)
- `o3` → o3-mini (reasoning model)
- `4o` → gpt-4o (legacy model)

## Output

Conversations are displayed in the terminal with Rich formatting and automatically saved to:
- `~/.pidgin_data/transcripts/YYYY-MM-DD/[conversation-id]/`
  - `conversation.json` - Machine-readable format
  - `conversation.md` - Human-readable markdown

## Features (Phase 1)

✅ AI-to-AI conversations between Claude and GPT models  
✅ Cross-provider conversations (e.g., Claude talking to GPT)  
✅ Real-time terminal display with Rich formatting  
✅ Automatic transcript saving (JSON + Markdown)  
✅ Graceful Ctrl+C handling  
✅ Secure API key handling via environment variables  
✅ Model shortcuts for convenience  
✅ CWD-agnostic operation (saves to ~/.pidgin_data/)

## Features

- **Multi-Provider Support**: Works with Anthropic, OpenAI, and Google AI models
- **Flexible Experiments**: Design custom communication scenarios and constraints
- **Rich Analysis**: Built-in metrics for compression, symbol usage, and linguistic patterns
- **Interactive UI**: Real-time visualization of conversations and metrics
- **Extensible Architecture**: Easy to add new providers, analyzers, and experiment types

## Project Structure

```
pidgin/
├── pidgin/
│   ├── providers/      # LLM provider implementations
│   ├── core/          # Core experiment and conversation logic
│   ├── analysis/      # Analysis tools and metrics
│   ├── storage/       # Data persistence layer
│   ├── ui/           # User interface components
│   ├── commands/     # CLI command implementations
│   ├── config/       # Configuration management
│   └── llm/          # LLM abstraction layer
├── tests/            # Test suite
├── docs/             # Documentation
├── pyproject.toml    # Project configuration
└── README.md         # This file
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