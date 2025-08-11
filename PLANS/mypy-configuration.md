# Mypy Type Checking Configuration Plan

## Overview

Mypy is a static type checker for Python that analyzes code without running it to find type-related bugs before runtime. For Pidgin, this is particularly valuable because:

1. **Research integrity**: Type errors in experiment configuration could invalidate results
2. **Complex configuration**: Multiple nested configs benefit from type validation
3. **Provider interfaces**: Ensures all providers implement required methods correctly
4. **Event system**: Validates event payloads match expected structures

## Benefits for Pidgin

### Immediate Benefits
- Catch configuration errors before experiments run
- Prevent API response parsing failures
- Ensure consistent provider implementations
- Document expected types for better collaboration

### Long-term Benefits
- Safer refactoring (like the recent run.py parameter reduction)
- Better IDE support and autocomplete
- Living documentation through type hints
- Reduced debugging time

## Configuration Strategy

### Phase 1: Permissive Setup (Week 1)
Start with lenient settings to avoid overwhelming the codebase with errors.

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
pretty = true
show_error_codes = true
show_error_context = true
warn_return_any = false  # Start permissive
warn_unused_configs = true
ignore_missing_imports = true  # For libraries without stubs
no_implicit_optional = true  # Require explicit Optional[]
check_untyped_defs = false  # Don't check untyped functions yet
```

### Phase 2: Core Modules (Week 2)
Apply stricter checking to already-typed modules:

```toml
# Strict for CLI (already has type hints)
[[tool.mypy.overrides]]
module = "pidgin.cli.*"
disallow_untyped_defs = true
warn_return_any = true

# Strict for models and configs
[[tool.mypy.overrides]]
module = [
    "pidgin.config.models",
    "pidgin.experiments.models",
    "pidgin.cli.run_handlers.models"
]
disallow_untyped_defs = true
```

### Phase 3: Gradual Expansion (Weeks 3-4)
Expand coverage to critical paths:

```toml
[[tool.mypy.overrides]]
module = [
    "pidgin.core.*",
    "pidgin.providers.base",
    "pidgin.events.*"
]
disallow_untyped_defs = true
warn_return_any = true
```

### Phase 4: Full Strictness (Month 2)
Eventually enable strict mode for entire codebase:

```toml
[tool.mypy]
strict = true  # Enables all strict checks
allow_untyped_decorators = true  # For Click decorators
```

## Common Patterns to Fix

### 1. Missing Return Types
```python
# Before
def get_experiment_config(name):
    return ExperimentConfig.load(name)

# After  
def get_experiment_config(name: str) -> ExperimentConfig:
    return ExperimentConfig.load(name)
```

### 2. Optional Handling
```python
# Before
def process_config(config):
    if config:
        return config.validate()

# After
def process_config(config: Optional[Config]) -> Optional[List[str]]:
    if config is not None:
        return config.validate()
    return None
```

### 3. Type Narrowing
```python
# Before
def handle_event(event):
    if isinstance(event, MessageEvent):
        print(event.content)  # mypy doesn't know event is MessageEvent

# After
def handle_event(event: Event) -> None:
    if isinstance(event, MessageEvent):
        # mypy now knows event is MessageEvent in this block
        print(event.content)
```

### 4. Generic Collections
```python
# Before
def get_providers():
    return ["anthropic", "openai"]

# After
def get_providers() -> List[str]:
    return ["anthropic", "openai"]
```

## Specific Fixes Needed

Based on current codebase analysis:

### CLI Module (`pidgin/cli/`)
- ✅ Already has type hints on main entry points
- Need: Add types to helper functions
- Need: Type callback functions properly

### Providers (`pidgin/providers/`)
```python
# Base class needs typing
class Provider(ABC):
    @abstractmethod
    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        ...
```

### Event System (`pidgin/events/`)
```python
# Events need proper typing
@dataclass
class Event:
    timestamp: datetime
    event_type: str
    payload: Dict[str, Any]  # Could be more specific
```

### Config Classes (`pidgin/config/`)
- Add types to all config loading methods
- Ensure Optional fields are marked correctly
- Add validation return types

## CI Integration

### GitHub Actions Setup
```yaml
# .github/workflows/type-check.yml
name: Type Check

on: [push, pull_request]

jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run mypy pidgin/
        continue-on-error: true  # Initially, then make required
```

### Pre-commit Hook (Optional)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## Development Workflow

### 1. Running mypy locally
```bash
# Check entire project
poetry run mypy pidgin/

# Check specific module
poetry run mypy pidgin/cli/

# Check with specific config
poetry run mypy --config-file pyproject.toml pidgin/
```

### 2. Handling errors
```python
# Temporary ignore for complex cases
result = complex_function()  # type: ignore[no-untyped-call]

# Document why ignoring
# type: ignore[arg-type]  # Third-party library has wrong stub
```

### 3. Type stubs for dependencies
```bash
# Install type stubs
poetry add --group dev types-pyyaml types-requests
```

## Module Priority Order

Based on importance and current state:

1. **High Priority** (Already partially typed)
   - `pidgin/cli/*` - Entry points, user-facing
   - `pidgin/config/*` - Critical for correct operation
   - `pidgin/experiments/*` - Core functionality

2. **Medium Priority** (Core logic)
   - `pidgin/providers/*` - API interfaces
   - `pidgin/events/*` - Event system
   - `pidgin/core/*` - Main engine

3. **Low Priority** (Can wait)
   - `pidgin/ui/*` - Display code
   - `pidgin/analysis/*` - Post-processing
   - Tests - Optional but helpful

## Success Metrics

### Phase 1 (Week 1)
- [ ] Mypy runs without crashing
- [ ] Less than 100 errors in permissive mode
- [ ] CI pipeline includes mypy (non-blocking)

### Phase 2 (Week 2)
- [ ] CLI module passes strict checks
- [ ] Config module fully typed
- [ ] Less than 50 errors total

### Phase 3 (Month 1)
- [ ] Core modules pass strict checks
- [ ] All public APIs have type hints
- [ ] CI blocks on type errors in typed modules

### Phase 4 (Month 2)
- [ ] 80% of codebase has type hints
- [ ] Strict mode enabled for new code
- [ ] Type checking required for all PRs

## Common Gotchas

### 1. Click decorators
Click's decorators can confuse mypy. Solution:
```python
from typing import Optional
import click

@click.command()
@click.option('--name', type=str)
def command(name: Optional[str]) -> None:
    ...
```

### 2. Async iterators
```python
async def stream() -> AsyncIterator[str]:
    yield "data"
```

### 3. Forward references
```python
from __future__ import annotations  # At top of file

class Node:
    def get_parent(self) -> Node:  # Can reference Node
        ...
```

## Resources

- [Mypy documentation](https://mypy.readthedocs.io/)
- [Type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [Common patterns](https://mypy.readthedocs.io/en/stable/common_issues.html)

## Next Steps

1. Add mypy to pyproject.toml dependencies
2. Create initial configuration (Phase 1)
3. Run baseline check and document errors
4. Fix critical type errors in CLI module
5. Gradually expand coverage per timeline

This plan provides a pragmatic approach to adopting type checking without disrupting active development, while ensuring Pidgin's critical paths become more robust and maintainable.