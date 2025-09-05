# Installation Guide

Pidgin requires Python 3.9 or later and can be installed using pip, pipx, uv, or from source.

## Prerequisites

- **Python 3.9+** (tested up to Python 3.13)
- **API Keys** for at least one provider:
  - Anthropic API key for Claude models
  - OpenAI API key for GPT models
  - Google API key for Gemini models
  - xAI API key for Grok models
  - Local models via Ollama (no API key needed)

## Quick Install

```bash
# Install as isolated CLI tool (choose one)
uv tool install pidgin-ai      # Recommended - fast
pipx install pidgin-ai          # Alternative

# Or install in current environment
uv pip install pidgin-ai        # Fast
pip install pidgin-ai           # Traditional
```

## Development Installation

### Using uv (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin

# Install with uv (extremely fast!)
uv sync

# Run pidgin
uv run pidgin --help

# Or build and install globally
uv build
pipx install dist/*.whl
```

### Using pip with Editable Install

```bash
# Clone the repository
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

## Setting Up API Keys

Pidgin looks for API keys in environment variables:

```bash
# Add to your ~/.bashrc, ~/.zshrc, or ~/.bash_profile
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."
```

Or create a `.env` file in your project directory:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
XAI_API_KEY=...
```

## Optional: Local Models with Ollama

For local model support, install Ollama:

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull models you want to use
ollama pull llama2
ollama pull mistral
ollama pull phi
```

## Verify Installation

Check that Pidgin is installed correctly:

```bash
# Check version
pidgin --version

# View help
pidgin --help

# List available models
pidgin models
```

Run a test conversation:

```bash
# Using local test model (no API needed)
pidgin run -a local:test -b local:test -t 3

# Using real models (requires API keys)
pidgin run -a claude-3-haiku -b gpt-4o-mini -t 5
```

## Platform-Specific Notes

### macOS
- Tested on macOS 12+ (Monterey and later)
- Apple Silicon (M1/M2/M3) fully supported
- Install command line tools if needed: `xcode-select --install`

### Linux
- Tested on Ubuntu 20.04+, Debian 11+, Fedora 35+
- Requires Python development headers: `sudo apt-get install python3-dev`

### Windows
- Use WSL2 for best compatibility
- Native Windows support is experimental
- Paths in examples use forward slashes (/)

## Troubleshooting

### Import Errors
If you see import errors, ensure you're using Python 3.9+:
```bash
python --version  # Should show 3.9 or higher
```

### API Key Issues
Verify your API keys are set:
```bash
# Check that your API keys are set
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY
```

### Permission Errors
On Unix systems, you may need to add `~/.local/bin` to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Ollama Connection
If using local models, ensure Ollama is running:
```bash
ollama list  # Should show available models
```

## Next Steps

- Read the [Quickstart Guide](quickstart.md) to run your first experiment
- See [CLI Usage](cli-usage.md) for detailed command documentation
- Check [Configuration](yaml-specs.md) for advanced setup options