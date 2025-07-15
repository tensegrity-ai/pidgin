# Pidgin Testing Standards

This document defines testing standards and best practices for the Pidgin project.

## Core Principles

### 1. Integration Tests Over Extensive Mocks
- **Prefer real components** when they're fast and reliable
- **Use in-memory DuckDB** for database tests (milliseconds vs seconds)
- **Mock only external dependencies**: APIs, network calls, file I/O when slow
- **Test behavior, not implementation**: Focus on what components do, not how

### 2. When to Mock vs Use Real Components

#### Use Real Components When:
- Testing DuckDB operations (use `in_memory_db` fixture)
- Testing EventBus (it's fast and file I/O can be directed to temp dirs)
- Testing metrics calculations (they're pure functions)
- Testing data transformations
- Testing CLI command logic (use CliRunner)

#### Mock When:
- Calling external APIs (Anthropic, OpenAI, etc.)
- Network operations that could fail or be slow
- System operations that could have side effects
- Time-sensitive operations (use freezegun)
- Testing error conditions hard to reproduce

## Database Testing Patterns

### Available Fixtures

```python
# Fast in-memory database for unit tests
def test_metrics_calculation(in_memory_db_with_schema):
    # Schema is already loaded, just insert test data
    in_memory_db_with_schema.execute("INSERT INTO conversations ...")
    
# File-based database for persistence tests  
def test_concurrent_access(file_based_db):
    # Test actual file operations, locking, etc.
    
# EventStore with in-memory backend
def test_event_operations(event_store_memory):
    # Fast EventStore operations without file I/O
```

### Example: Refactoring from Mocks to Integration

❌ **Before (Over-mocked)**:
```python
def test_save_conversation():
    mock_store = Mock()
    mock_store.save_conversation = AsyncMock(return_value="conv_123")
    
    # This doesn't test actual database behavior!
    result = await mock_store.save_conversation(conversation)
    assert result == "conv_123"
```

✅ **After (Integration test)**:
```python
async def test_save_conversation(event_store_memory):
    # Test with real database operations
    conversation = make_conversation()
    conv_id = await event_store_memory.save_conversation(conversation)
    
    # Verify data was actually saved
    saved = await event_store_memory.get_conversation(conv_id)
    assert saved.id == conversation.id
    assert len(saved.messages) == len(conversation.messages)
```

## Test Organization

### File Size Limits
- **300 lines max** per test file
- Break large test files by feature or component
- Group related tests in classes

### Test Naming
```python
# Clear, descriptive test names
def test_convergence_metric_increases_with_vocabulary_overlap():
    ...

# Not just "test_convergence"
def test_convergence():  # Bad
    ...
```

## Using Advanced Testing Tools

### Property-Based Testing with Hypothesis

Use for algorithmic code and data processing:

```python
from hypothesis import given, strategies as st

@given(
    messages=st.lists(
        st.text(min_size=1, max_size=1000),
        min_size=2,
        max_size=100
    )
)
def test_vocabulary_overlap_properties(messages):
    # Test that vocabulary overlap is always between 0 and 1
    overlap = calculate_vocabulary_overlap(messages)
    assert 0 <= overlap <= 1
```

### Realistic Test Data with Faker

Use the provided fixtures for realistic test scenarios:

```python
def test_conversation_flow(realistic_conversation_generator):
    # Generate a technical conversation
    conversation = realistic_conversation_generator(
        num_turns=20, 
        topic="technical"
    )
    
    # Test with realistic data
    metrics = calculate_all_metrics(conversation)
    assert metrics.average_message_length > 0
```

### Time-Based Testing with Freezegun

```python
from freezegun import freeze_time

@freeze_time("2024-01-01 12:00:00")
def test_rate_limiting():
    # Time is frozen, test rate limit behavior
    limiter = RateLimiter(requests_per_minute=60)
    
    for _ in range(60):
        assert limiter.check_rate_limit() is True
    
    # 61st request should be blocked
    assert limiter.check_rate_limit() is False
```

## Performance Testing

### Benchmarking Critical Paths

```python
import time
import pytest

@pytest.mark.benchmark
def test_metrics_performance(in_memory_db_with_schema, benchmark):
    # Setup test data
    setup_large_conversation(in_memory_db_with_schema, num_messages=1000)
    
    # Benchmark the operation
    result = benchmark(calculate_all_metrics, in_memory_db_with_schema)
    
    # Assert performance requirements
    assert benchmark.stats['mean'] < 0.1  # Must complete in 100ms
```

## Coverage Guidelines

### Target Coverage by Component

- **Core Logic** (metrics, events, conductor): 90%+
- **Database Operations**: 80%+
- **CLI Commands**: 70%+ (focus on logic, not argparse)
- **Utilities**: 60%+ (some defensive code is OK to skip)
- **UI/Display**: 50%+ (visual output is hard to test)

### Acceptable Coverage Gaps

- Defensive programming for "impossible" states
- CLI boilerplate (argument parsing)
- Logging statements
- Simple property getters/setters
- Error messages that are hard to trigger

## Test Categories

Mark tests appropriately:

```python
@pytest.mark.unit
def test_calculate_overlap():
    # Fast, isolated unit test
    
@pytest.mark.integration
def test_full_conversation_flow():
    # Slower test with real components
    
@pytest.mark.slow
def test_large_experiment():
    # Tests that take >1 second
    
@pytest.mark.database
def test_concurrent_db_access():
    # Tests requiring real database
```

## Running Tests

```bash
# Run all fast tests (default)
pytest

# Run with coverage report
pytest --cov=pidgin --cov-report=html

# Run only unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Run slow tests
pytest --runslow

# Run specific test file
pytest tests/unit/test_metrics.py

# Run tests matching pattern
pytest -k "convergence"

# Run failed tests from last run
pytest --lf

# Stop on first failure
pytest -x
```

## Best Practices Summary

1. **Start with integration tests** - they catch real bugs
2. **Use in-memory databases** - they're fast enough for unit tests
3. **Mock at boundaries** - external services, not internal components
4. **Generate realistic test data** - use faker fixtures
5. **Test properties, not just examples** - use hypothesis for robustness
6. **Keep tests focused** - one concept per test
7. **Make tests fast** - parallelize, use in-memory DBs
8. **Document complex tests** - explain the "why"

## Example Test File Structure

```python
"""Test convergence metrics calculation."""

import pytest
from hypothesis import given, strategies as st

from pidgin.metrics.convergence_metrics import ConvergenceCalculator


class TestConvergenceCalculator:
    """Test the convergence calculator with various scenarios."""
    
    def test_identical_messages_show_perfect_convergence(self, in_memory_db):
        """Messages with identical vocabulary should show convergence = 1.0."""
        # Setup
        messages = create_identical_messages(count=10)
        calculator = ConvergenceCalculator(in_memory_db)
        
        # Execute
        convergence = calculator.calculate(messages)
        
        # Assert
        assert convergence == 1.0
    
    def test_different_languages_show_no_convergence(self, faker_factory):
        """Messages in different languages should show convergence near 0."""
        # Generate messages in different languages
        english_msgs = faker_factory.sentences(nb=5, locale='en')
        spanish_msgs = faker_factory.sentences(nb=5, locale='es')
        
        # Test shows no convergence
        convergence = calculate_convergence(english_msgs, spanish_msgs)
        assert convergence < 0.1
    
    @given(st.lists(st.text(min_size=1), min_size=2, max_size=50))
    def test_convergence_is_always_normalized(self, messages):
        """Property: convergence is always between 0 and 1."""
        convergence = calculate_convergence(messages)
        assert 0 <= convergence <= 1
```

Remember: Good tests give confidence that your code works correctly. Achieving this with simpler tests that use real components is better than complex mock setups that might miss real issues.