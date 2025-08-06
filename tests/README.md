# Minimal Test Suite

This is a deliberately minimal test suite. We have ~10 tests that verify the core system works.

## Philosophy

- If it passes, the system works
- If it fails, there's a real problem
- No flaky tests
- No implementation detail tests
- No 100% coverage goals

## The Tests

1. **test_conversation.py** - Core system works end-to-end
2. **test_error_handling.py** - Doesn't crash on errors  
3. **test_cli.py** - CLI doesn't explode
4. **test_database.py** - Can import and analyze data
5. **test_metrics.py** - Metrics are sane
6. **test_post_processing.py** - Post-processing pipeline works ✨

## Running Tests

```bash
# Run all tests
poetry run pytest tests/

# Run during development
poetry run pytest tests/ -x  # Stop on first failure

# Run specific test
poetry run pytest tests/integration/test_conversation.py
```

## Current Status

```bash
poetry run pytest tests/ -v
# ====== 11 passed in 1.98s ======
```

- ✅ **ALL 11 TESTS PASSING**
- ✅ CLI tests (4/4)
- ✅ Integration tests (3/3)
- ✅ Metrics tests (2/2)
- ✅ Database test (1/1)
- ✅ Post-processing test (1/1)

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