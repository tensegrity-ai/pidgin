# Contributing to Pidgin

Thank you for your interest in contributing to Pidgin! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive. We're all here to advance the understanding of AI communication patterns.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/pidgin.git`
3. Install in development mode: `pip install -e ".[dev]"`
4. Create a branch: `git checkout -b feature/your-feature-name`

## Development Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy pidgin/

# Run linting
ruff check pidgin/
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

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Documentation improvements
- General questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).