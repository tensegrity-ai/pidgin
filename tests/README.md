# Minimal Test Suite

This is a deliberately minimal test suite that verifies the core system works.

## Philosophy

- If it passes, the system works
- If it fails, there's a real problem
- No flaky tests
- No implementation detail tests
- No 100% coverage goals

## The Tests

### Integration Tests
1. **test_conversation.py** - Core system works end-to-end
2. **test_full_experiment.py** - Complete experiment pipeline including parallel execution
3. **test_error_handling.py** - Graceful error handling
4. **test_database.py** - JSONL → DuckDB import flow
5. **test_metrics.py** - Metric calculations are sane
6. **test_post_processing.py** - Analysis pipeline works
7. **test_event_deserialization.py** - Event system integrity
8. **test_type_safety.py** - Type system validation
9. **test_daemon_subprocess.py** - Process management

### CLI Tests
- **test_cli.py** - CLI commands work correctly

## Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run during development
uv run pytest tests/ -x  # Stop on first failure

# Run specific test
uv run pytest tests/integration/test_conversation.py

# Run with coverage
uv run pytest --cov=pidgin

# Run in parallel
uv run pytest -n auto
```

## Current Status

```bash
uv run pytest tests/ -q
# ====== 33 passed in ~8s ======
```

- ✅ **ALL TESTS PASSING**
- ✅ Integration tests (32)
- ✅ CLI tests (1)
- ✅ Parallel execution test
- ✅ Error classification

## When to Add Tests

Only when:
1. A user reports a bug
2. You're adding a complex feature
3. You're genuinely worried something will break

## When to Delete Tests

When:
1. They become flaky
2. They take >5 seconds
3. They test implementation details
4. You have to update them every refactor

## Coverage

We don't care. If the 10 tests pass, the system works.