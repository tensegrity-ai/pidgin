# Pidgin Codebase Audit Report & Action Plan

## Executive Summary

The Pidgin codebase audit reveals a well-structured project with clean architecture but several areas needing improvement. Most critical issues relate to missing tests, god objects, thread safety, and code duplication.

## Critical Issues (Must Fix)

### 1. **No Test Suite** 🚨
- Zero test files despite test dependencies in pyproject.toml
- Coverage file exists but no tests to generate it
- **Action**: Create comprehensive test suite starting with core modules

### 2. **Thread Safety Problems** 🚨
- 14 modules use shared mutable state without proper locking
- Race conditions possible in manifest updates and JSONL writes
- **Action**: Add asyncio.Lock to all shared state access

### 3. **God Objects** 🚨
- EventStore (856 lines, 22 methods)
- MetricsCalculator (437 lines, 21 methods)
- **Action**: Split into focused, single-responsibility classes

## High Priority Issues

### 4. **Code Duplication**
- Provider error handling duplicated across 3+ files
- Context truncation logic repeated
- **Action**: Extract to base classes or utility modules

### 5. **Inconsistent Error Handling**
- Google provider has basic error handling
- Bare except clauses in multiple files
- **Action**: Standardize error handling across all providers

### 6. **Long Methods**
- 67 methods over 50 lines
- Several over 100 lines (e.g., run_conversation: 142 lines)
- **Action**: Decompose into smaller, focused methods

## Medium Priority Issues

### 7. **Magic Strings/Numbers**
- 250+ hardcoded status strings
- Hardcoded paths and values
- **Action**: Move all to constants module

### 8. **Naming Inconsistencies**
- Mixed abbreviations: conv/conversation, exp/experiment
- Agent naming: agent_a vs model_a
- **Action**: Standardize on full names

### 9. **Missing Validation**
- No validation for convergence weights sum
- Missing config value validation
- **Action**: Add comprehensive input validation

## Low Priority Issues

### 10. **Documentation/Organization**
- Orphaned nested pidgin_output directory
- Temporary files (banner_options.txt)
- .DS_Store files not gitignored
- **Action**: Clean up repository

### 11. **Minor Code Quality**
- 5 TODO comments to address
- Unused ConversationError exception
- Empty pass statements (acceptable for hierarchy)

## Proposed Implementation Plan

### Phase 1: Critical Safety (Week 1)
1. Add asyncio locks to EventBus, ManifestManager, EventHandler
2. Fix race conditions in JSONL writes
3. Create initial test suite for core modules

### Phase 2: Architecture Refactoring (Week 2-3)
1. Split EventStore into:
   - ConversationRepository
   - ExperimentRepository  
   - MetricsRepository
2. Refactor long methods in conductor.py and message_handler.py
3. Extract provider base functionality

### Phase 3: Code Quality (Week 4)
1. Create constants.py with all magic values
2. Standardize naming conventions
3. Add validation to config and inputs
4. Address TODO comments

### Phase 4: Testing & Documentation (Week 5)
1. Achieve 80% test coverage
2. Add integration tests for concurrent operations
3. Update documentation with new architecture
4. Clean up repository structure

## Recommended Tools & Practices

1. **Pre-commit hooks**: Add ruff, black, mypy
2. **CI/CD**: Set up GitHub Actions for tests
3. **Code quality**: Add SonarQube or similar
4. **Documentation**: Auto-generate from docstrings

## Positive Findings

- Clean module separation
- Good use of protocols and abstractions
- Event-driven architecture well implemented
- Consistent use of async/await
- Clear configuration system
- Good separation of concerns at module level

The codebase is fundamentally sound with good architecture. The issues found are typical of a rapidly developed research tool and can be systematically addressed without major rewrites.

## Specific Code Smells Found

### God Objects
1. **EventStore** (`pidgin/database/event_store.py:1-856`)
   - 22 methods handling conversations, experiments, metrics, tokens
   - Should be split into focused repositories

2. **MetricsCalculator** (`pidgin/metrics/calculator.py:1-437`)
   - 21 methods mixing calculation, analysis, and formatting
   - Needs separation of concerns

### Long Methods
1. `conductor.run_conversation()` (`pidgin/core/conductor.py:117-259`) - 142 lines
2. `message_handler.get_agent_message()` (`pidgin/core/message_handler.py:39-191`) - 152 lines
3. `experiment_runner._run_single_conversation()` (`pidgin/experiments/runner.py:234-368`) - 134 lines
4. `event_store.import_experiment()` (`pidgin/database/event_store.py:542-646`) - 104 lines

### Thread Safety Issues
1. **EventBus** (`pidgin/core/event_bus.py:15-20`) - `_jsonl_files` dict without locks
2. **ManifestManager** (`pidgin/experiments/manifest.py:various`) - mix of threading.Lock and no asyncio locks
3. **EventHandler** classes - manage per-conversation state dicts without protection

### Code Duplication
1. **Error handling** duplicated in:
   - `pidgin/providers/anthropic.py:96-114`
   - `pidgin/providers/openai.py:189-205`
   - Should be extracted to base class

2. **Context truncation** duplicated in:
   - `pidgin/providers/anthropic.py:151-166`
   - `pidgin/providers/openai.py:240-254`
   - `pidgin/providers/google.py:136-150`

### Hardcoded Values
1. Max tokens: `pidgin/providers/anthropic.py:181`, `pidgin/providers/openai.py:272`
2. Config path: `pidgin/config/config.py:140`
3. Status strings throughout codebase (250+ instances)

### Bare Except Clauses
1. `pidgin/cli/helpers.py:105-110` - `check_ollama_available()`
2. `pidgin/database/async_duckdb.py:various` - multiple empty except blocks
3. `pidgin/monitor/system_monitor.py:various` - empty exception handlers