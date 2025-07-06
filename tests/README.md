# Pidgin Test Suite

This test suite provides comprehensive testing for the Pidgin AI conversation research tool.

## Structure

```
tests/
├── unit/                   # Unit tests for individual modules
│   ├── test_types.py      # Core data types
│   ├── test_token_utils.py # Token counting utilities
│   ├── test_name_generator.py # Experiment name generation
│   ├── test_paths.py      # Path utilities
│   ├── test_event_bus.py  # Event system
│   ├── test_manifest.py   # Manifest management
│   └── test_retry_utils.py # Retry logic
├── integration/           # Integration tests
│   └── test_conversation_flow.py # End-to-end conversation tests
├── fixtures/              # Shared test fixtures
│   ├── events.py         # Event fixtures
│   ├── messages.py       # Message and conversation fixtures
│   └── providers.py      # Mock provider implementations
└── conftest.py           # Pytest configuration

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

Current test coverage includes:

### Unit Tests (73 tests)
- **Core Types** (10 tests): Message, Agent, Conversation, ConversationTurn
- **Event Bus** (11 tests): Event emission, subscription, history, JSONL logging
- **Token Utils** (12 tests): Token estimation, usage parsing
- **Path Utils** (9 tests): Output directory resolution, environment variables
- **Name Generator** (5 tests): Experiment name generation
- **Manifest Manager** (13 tests): Experiment manifest CRUD, atomic writes
- **Retry Utils** (13 tests): Exponential backoff, error detection

### Integration Tests (3 tests)
- Basic conversation flow with test model
- Event serialization to JSONL
- Error handling during conversations

### Test Fixtures
- Common event types for testing
- Sample messages and conversations
- Mock providers (MockProvider, ErrorProvider, DelayedProvider)

## TODO: Additional Tests Needed

### Unit Tests
1. **Metrics Calculator** - Complex metrics calculations
2. **Rate Limiter** - Token bucket algorithm, provider-specific limits
3. **Conductor** - Conversation orchestration
4. **Message Handler** - Message routing and processing
5. **Provider Implementations** - API interactions (with mocking)

### Integration Tests
1. **Full Experiment Flow** - Complete experiment lifecycle
2. **Database Operations** - Event storage and retrieval
3. **CLI Commands** - Command parsing and execution
4. **Multi-Conversation Experiments** - Parallel execution

### Performance Tests
1. **Large Conversations** - Memory usage, event handling
2. **Concurrent Experiments** - Resource management
3. **JSONL File Handling** - Large file operations

## Testing Best Practices

1. **Use Fixtures** - Leverage pytest fixtures for common test data
2. **Mock External Dependencies** - Don't make real API calls
3. **Test Error Cases** - Include negative test cases
4. **Keep Tests Fast** - Use small datasets, mock delays
5. **Test Isolation** - Each test should be independent
6. **Clear Assertions** - Make test failures easy to understand

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies required
- Uses temporary directories for file operations
- Mocks all API interactions
- Predictable and reproducible results