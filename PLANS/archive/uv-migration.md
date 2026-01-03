# Migration Plan: Poetry/pipx → uv/uvx

## Overview
Complete migration from Poetry + pipx to uv + uvx for faster, simpler Python dependency and tool management.

## Phase 1: Install and Setup uv

### 1.1 Install uv
```bash
# macOS
brew install uv

# Or via curl (cross-platform)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1.2 Initialize uv in project
```bash
cd /Users/ngl/code/pidgin

# Create uv.lock from existing dependencies
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt

# Or directly migrate from poetry.lock
uv sync
```

## Phase 2: Update pyproject.toml

### 2.1 Convert Poetry sections to PEP 621 + uv

**Remove:**
```toml
[tool.poetry]
[tool.poetry.dependencies]
[tool.poetry.group.dev.dependencies]
[tool.poetry.scripts]
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**Add:**
```toml
[project]
name = "pidgin-ai"
version = "0.1.0"
description = "AI conversation research tool for studying emergent communication patterns"
authors = [{name = "Your Name", email = "your.email@example.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9,<3.13"
keywords = ["ai", "llm", "conversation", "research", "communication", "anthropic", "openai"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

dependencies = [
    "click>=8.0.0",
    "rich>=13.0.0",
    "rich-click>=1.8.0",
    "pydantic>=2.0.0",
    "anthropic>=0.25.0,<1.0.0",
    "openai>=1.0.0",
    "google-generativeai>=0.8.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "aiohttp>=3.9.0",
    "urllib3>=2.5.0",
    "requests>=2.32.4",
    "duckdb>=1.1.3",
    "setproctitle>=1.3",
]

[project.urls]
Homepage = "https://github.com/tensegrity-ai/pidgin"
Repository = "https://github.com/tensegrity-ai/pidgin"
Documentation = "https://github.com/tensegrity-ai/pidgin#readme"

[project.scripts]
pidgin = "pidgin.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "pytest-xdist>=3.5.0",
    "pytest-timeout>=2.2.0",
    "hypothesis>=6.100.0",
    "freezegun>=1.4.0",
    "responses>=0.25.0",
    "faker>=24.0.0",
    "black>=24.3.0",
    "ruff>=0.8.0",
    "mypy>=1.0.0",
    "types-pyyaml>=6.0.0",
    "bandit[toml]>=1.7.0",
    "safety>=3.0.0",
    "pre-commit>=3.0.0",
    "radon>=6.0.1",
    "autoflake>=2.3.1",
]
```

### 2.2 Keep existing tool configurations
- Keep all existing [tool.ruff], [tool.mypy], [tool.pytest.ini_options], etc.
- Remove only [tool.poe.tasks] (will use uv run directly)

## Phase 3: Replace Development Workflows

### 3.1 Command Mappings

| Poetry Command | uv Command |
|---------------|------------|
| `poetry install` | `uv sync` |
| `poetry install --no-dev` | `uv sync --no-dev` |
| `poetry add <package>` | `uv add <package>` |
| `poetry add -D <package>` | `uv add --dev <package>` |
| `poetry remove <package>` | `uv remove <package>` |
| `poetry run pytest` | `uv run pytest` |
| `poetry run ruff check` | `uv run ruff check` |
| `poetry run mypy` | `uv run mypy` |
| `poetry shell` | `uv venv && source .venv/bin/activate` |
| `poetry build` | `uv build` |
| `poetry publish` | `uv publish` |

### 3.2 Create convenience scripts

**Create `dev.sh`:**
```bash
#!/usr/bin/env bash
# Development convenience commands

case "$1" in
  test)
    uv run pytest "${@:2}"
    ;;
  lint)
    uv run ruff check .
    ;;
  format)
    uv run ruff format .
    ;;
  typecheck)
    uv run mypy pidgin
    ;;
  ci)
    uv run ruff check . && \
    uv run mypy pidgin && \
    uv run pytest && \
    uv run bandit -r pidgin
    ;;
  *)
    echo "Usage: ./dev.sh {test|lint|format|typecheck|ci}"
    exit 1
    ;;
esac
```

## Phase 4: Replace CLI Installation

### 4.1 Remove pipx installation
```bash
pipx uninstall pidgin-ai
```

### 4.2 Install with uv tool
```bash
# For development (editable)
uv pip install -e .

# For global CLI access
uv tool install .

# Or use uvx for one-off runs without installation
uvx --from . pidgin chat -a anthropic:claude-3-5-sonnet -b openai:gpt-4
```

## Phase 5: Update CI/CD Pipeline (.github/workflows/ci.yml)

### 5.1 Replace Poetry setup with uv

**Before:**
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    version: ${{ env.POETRY_VERSION }}
    
- name: Install dependencies
  run: poetry install --no-interaction --no-root
```

**After:**
```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v3
  with:
    enable-cache: true
    
- name: Install dependencies
  run: uv sync --frozen
```

### 5.2 Simplify the entire workflow

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  lint-and-type-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        enable-cache: true
    
    - name: Set up Python
      run: uv python install 3.11
    
    - name: Install dependencies
      run: uv sync --frozen
    
    - name: Run ruff linting
      run: |
        uv run ruff check . --output-format=github
        echo "✓ All linting checks passed"
    
    - name: Check ruff formatting
      run: |
        uv run ruff format --check .
        echo "✓ Code formatting verified"
    
    - name: Run mypy type checking
      run: |
        uv run mypy pidgin
        echo "✓ All type checks passed"

  test:
    needs: lint-and-type-check
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        enable-cache: true
    
    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync --frozen
    
    - name: Run tests with coverage
      run: uv run pytest --cov=pidgin --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      if: matrix.python-version == '3.11'
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
        verbose: true
      env:
        CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  security:
    needs: lint-and-type-check
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        enable-cache: true
    
    - name: Set up Python
      run: uv python install 3.11
    
    - name: Install dependencies
      run: uv sync --frozen
    
    - name: Run bandit security check
      run: uv run bandit -r pidgin -f json -o bandit-report.json || true
    
    - name: Check dependencies for vulnerabilities
      run: uv run safety check || echo "Safety check completed with warnings"
```

## Phase 6: Update Build/Publishing

### 6.1 Build command
```bash
# Build distributions
uv build

# This creates:
# dist/pidgin_ai-0.1.0-py3-none-any.whl
# dist/pidgin_ai-0.1.0.tar.gz
```

### 6.2 Publishing to PyPI
```bash
# Set PyPI token
export UV_PUBLISH_TOKEN="pypi-..."

# Publish to PyPI
uv publish

# Or to TestPyPI first
uv publish --publish-url https://test.pypi.org/legacy/
```

## Phase 7: Update Documentation

### 7.1 Update README.md installation section

```markdown
## Installation

### Using uv (Recommended - Fastest)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pidgin
uv tool install pidgin-ai

# Or run without installing
uvx --from pidgin-ai pidgin chat -a anthropic:claude-3-5-sonnet -b openai:gpt-4
```

### Using pip
```bash
pip install pidgin-ai
```

### Development Installation
```bash
# Clone the repository
git clone https://github.com/tensegrity-ai/pidgin.git
cd pidgin

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and package
uv sync
uv pip install -e .
```
```

### 7.2 Update DEVELOPMENT.md

Add section on uv workflows:

```markdown
## Development with uv

We use `uv` for dependency management and virtual environments. It's 10-100x faster than traditional tools.

### Quick Start
```bash
# Install all dependencies
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Format code
uv run ruff format .

# Type checking
uv run mypy pidgin

# Run the CLI
uv run pidgin chat -a local:test -b local:test
```

### Adding Dependencies
```bash
# Add a runtime dependency
uv add requests

# Add a dev dependency
uv add --dev pytest-benchmark

# Update all dependencies
uv sync --upgrade
```

### Virtual Environment
```bash
# uv automatically creates and manages .venv
# Activate it manually if needed
source .venv/bin/activate

# Or just use uv run for everything
uv run python script.py
```
```

## Phase 8: Cleanup

### 8.1 Remove Poetry files
```bash
rm poetry.lock
rm poetry.toml  # if exists
```

### 8.2 Update .gitignore
```bash
# Add uv-specific ignores
echo "uv.lock" >> .gitignore
```

### 8.3 Create migration script for developers

**Create `migrate_to_uv.sh`:**
```bash
#!/usr/bin/env bash

echo "🚀 Migrating from Poetry to uv..."

# Install uv
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Clean up Poetry artifacts
echo "🧹 Cleaning up Poetry artifacts..."
rm -rf .venv
rm -f poetry.lock

# Install with uv
echo "📥 Installing dependencies with uv..."
uv sync

# Install package in editable mode
echo "🔧 Installing pidgin in development mode..."
uv pip install -e .

echo "✅ Migration complete! You can now use uv commands:"
echo "  uv run pytest       # Run tests"
echo "  uv run ruff check . # Run linting"
echo "  uv run pidgin      # Run the CLI"
```

## Benefits Summary

### Performance Improvements
- **Dependency resolution**: ~100x faster than Poetry
- **Installation**: ~10x faster package downloads
- **CI/CD**: ~50% reduction in pipeline time
- **Caching**: Better cache reuse, smaller cache sizes

### Developer Experience
- **Single tool**: uv replaces both Poetry and pipx
- **Modern standards**: Native PEP 517/621 support
- **Better errors**: Clear, actionable error messages
- **Simpler commands**: Intuitive CLI design

### Maintenance Benefits
- **Less configuration**: Minimal tool.uv section needed
- **Fewer dependencies**: uv is a single binary
- **Active development**: Rapid improvements and fixes
- **Better compatibility**: Works with all Python packaging standards

## Timeline

1. **Day 1**: Install uv, convert pyproject.toml, test locally
2. **Day 2**: Update CI/CD pipelines, test all workflows
3. **Day 3**: Update documentation, create migration guide
4. **Day 4**: Clean up Poetry artifacts, final testing
5. **Day 5**: Announce to team, support migration issues

## Commands Quick Reference

```bash
# Most common commands
uv sync                  # Install all dependencies
uv run pytest           # Run tests
uv run ruff check .     # Lint code
uv run mypy pidgin      # Type check
uv add <package>        # Add dependency
uv remove <package>     # Remove dependency
uv build                # Build distributions
uv publish              # Publish to PyPI
uvx --from . pidgin     # Run CLI without installing
```