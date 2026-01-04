# Contributing to Pidgin

Thank you for your interest in contributing to Pidgin! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive. We're all here to advance the understanding of AI communication patterns.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/pidgin.git`
3. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
4. Install dependencies: `uv sync`
5. Create a branch: `git checkout -b feature/your-feature-name`

## Development Workflow

```bash
# Install dependencies
uv sync

# Run development version
uv run pidgin run -a local:test -b local:test

# Run tests
uv run pytest

# Format code
uv run ruff format pidgin tests

# Check code style
uv run ruff check pidgin tests

# Type checking
uv run mypy pidgin

# Build package
uv build

# Install globally with pipx
pipx install dist/*.whl

# Clean experiment data
rm -rf ~/pidgin_output/
```

## Making Changes

### Code Style
- Follow PEP 8
- Use type hints for all public APIs
- Add Google-style docstrings to new functions/classes
- Keep line length under 100 characters

### Testing
- Add tests for new functionality
- Ensure all tests pass: `pytest`
- Maintain or improve code coverage

### Documentation
- Update relevant documentation
- Add docstrings to new code
- Update README.md if adding features
- Update man pages if changing CLI

## Submitting Changes

1. Commit your changes with clear messages:
   ```
   git commit -m "feat: add semantic similarity metric"
   git commit -m "fix: handle rate limit in OpenAI provider"
   git commit -m "docs: update metrics documentation"
   ```

2. Push to your fork: `git push origin feature/your-feature-name`

3. Create a Pull Request with:
   - Clear description of changes
   - Any relevant issue numbers
   - Screenshots/examples if applicable

## Commit Message Format

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

## Areas for Contribution

### High Priority
- Statistical significance testing
- Additional metrics (with justification)
- Performance optimizations
- Bug fixes

### Documentation
- Improve examples
- Add tutorials
- Clarify existing docs

### Testing
- Increase test coverage
- Add integration tests
- Test edge cases

## Philosophy

Remember Pidgin's core philosophy:
- **Observe**, don't interpret
- **Record**, don't theorize
- **Measure**, don't speculate
- Keep it lightweight and fast

For detailed development guidelines, architecture decisions, and design philosophy, see [CLAUDE.md](CLAUDE.md).

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Documentation improvements
- General questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).