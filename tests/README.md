# Pidgin Test Suite

Comprehensive test coverage for the Pidgin AI conversation research tool with 988 tests achieving 65.23% code coverage.

## Structure

```
tests/
├── unit/ (43 tests)           # Unit tests for core components
│   ├── test_conductor*.py     # Conversation orchestration
│   ├── test_event_*.py        # Event system and serialization
│   ├── test_metrics_*.py      # Metrics calculation and validation
│   ├── test_context_*.py      # Context management
│   ├── test_display_*.py      # Display utilities
│   └── (35+ more test files)  # See full list below
├── database/ (4 tests)        # Database and storage tests
│   ├── test_event_store.py    # Event storage
│   ├── test_repositories.py   # Repository patterns
│   ├── test_sync_event_store.py # Synchronous operations
│   └── test_transcript_generator.py # Transcript generation
├── integration/ (1 test)      # End-to-end integration tests
│   └── test_conversation_flow.py # Full conversation lifecycle
├── experiments/ (2 tests)     # Experiment runner tests
│   ├── test_runner_simple.py  # Basic experiment execution
│   └── test_state_builder.py  # State management
├── providers/ (2 tests)       # Provider implementation tests
│   ├── test_base.py          # Base provider interface
│   └── test_local.py         # Local test provider
├── cli/ (1 test)             # CLI command tests
│   └── test_run.py           # Run command tests
├── monitor/ (1 test)         # Monitor system tests
│   └── test_monitor.py       # System monitoring
├── ui/ (1 test)              # UI component tests
│   └── test_tail_display.py  # Tail display functionality
├── fixtures/                  # Shared test fixtures and builders
│   ├── events.py             # Event fixtures
│   ├── messages.py           # Message and conversation fixtures
│   └── providers.py          # Mock provider implementations
├── builders.py               # Test data builders
└── conftest.py               # Pytest configuration and fixtures
```

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=pidgin

# Run specific test file
poetry run pytest tests/unit/test_event_bus.py

# Run with verbose output
poetry run pytest -v

# Run tests matching pattern
poetry run pytest -k "event"
```

## Test Coverage

Current test suite: **988 tests** with **65.23% code coverage**

### Coverage by Component

#### Core Components (100% coverage)
- **Event System**: Event bus, event types, serialization/deserialization
- **Type System**: Message, Agent, Conversation, Turn data structures
- **Metrics**: Calculator, display, text analysis, convergence metrics
- **Utilities**: Token counting, path resolution, retry logic, display utils

#### High Coverage (90-99%)
- **Conductor**: Conversation orchestration and lifecycle (100%)
- **Message Handler**: Message routing and processing (98%)
- **Rate Limiter**: Token bucket implementation (98%)
- **Context Management**: Token limits and truncation (91%)
- **Database**: Event store, repositories, schema (90%+)

#### Moderate Coverage (50-89%)
- **Experiments**: Runner, state builder, manifest (73%)
- **CLI**: Commands and helpers (30-50%)
- **Monitor**: System monitoring (53%)

#### Low Coverage (< 50%)
- **Providers**: API implementations (10-36%) - uses mocks in tests
- **UI**: Display filters and chat mode (13-29%)
- **Analysis**: Notebook generator (0%) - not critical path

### Test Categories

1. **Unit Tests** (43 files, ~900 tests)
   - Comprehensive coverage of all core components
   - Fast execution with mocked dependencies
   - Property-based testing with Hypothesis
   - Extensive edge case coverage

2. **Integration Tests** (8 files, ~80 tests)
   - Database operations with real DuckDB
   - Full conversation lifecycle testing
   - Experiment execution workflows
   - CLI command integration

3. **UI/Monitor Tests** (2 files, ~8 tests)
   - Terminal display components
   - System monitoring functionality

## Test Execution

### Quick Test Commands

```bash
# Run all tests with coverage
poetry run pytest

# Run tests without coverage (faster)
poetry run pytest --no-cov

# Run specific test categories
poetry run pytest tests/unit/          # Unit tests only
poetry run pytest tests/integration/   # Integration tests
poetry run pytest tests/database/      # Database tests

# Run tests matching a pattern
poetry run pytest -k "event"          # All event-related tests
poetry run pytest -k "not slow"       # Skip slow tests

# Run with specific markers
poetry run pytest -m "unit"           # Unit tests only
poetry run pytest -m "not benchmark"  # Skip benchmarks

# Parallel execution (faster)
poetry run pytest -n auto             # Use all CPU cores
```

### Coverage Reports

```bash
# Generate HTML coverage report
poetry run pytest --cov=pidgin --cov-report=html
# Open htmlcov/index.html in browser

# Show missing lines in terminal
poetry run pytest --cov=pidgin --cov-report=term-missing

# Generate multiple report formats
poetry run pytest --cov=pidgin --cov-report=term --cov-report=html --cov-report=xml
```

## Key Test Files

### Most Important Test Files
1. **test_conductor.py** - Core conversation orchestration logic
2. **test_event_bus.py** - Event system that powers everything
3. **test_metrics_calculator.py** - Metrics calculation accuracy
4. **test_conversation_flow.py** - End-to-end integration test
5. **test_event_store.py** - Data persistence layer

### Test Utilities
- **builders.py** - Factory functions for test data
- **conftest.py** - Shared fixtures and pytest configuration
- **fixtures/** - Reusable test components

## Testing Best Practices

1. **Fast Execution** - Full suite runs in ~90 seconds
2. **No External Dependencies** - All API calls are mocked
3. **Deterministic** - Tests use fixed seeds and timestamps
4. **Isolated** - Each test cleans up after itself
5. **Comprehensive** - Edge cases, error paths, and happy paths
6. **Well-Organized** - Clear naming and logical grouping

## Test Markers

```python
# Available pytest markers (see pyproject.toml)
@pytest.mark.unit         # Fast unit tests
@pytest.mark.integration  # Integration tests
@pytest.mark.slow        # Tests taking >1 second
@pytest.mark.database    # Tests requiring DuckDB
@pytest.mark.benchmark   # Performance benchmarks
```

## Python Version Compatibility

Tests are compatible with Python 3.9+ and have been verified on:
- Python 3.9 (minimum supported)
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13 (current development)