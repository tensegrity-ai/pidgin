# Code Quality Improvement Plan

## Overview
Code smell analysis performed on 2025-08-10 after refactoring subprocess/daemon functionality.

## Critical Issues

### 1. Oversized Modules (Violates 200-line guideline)
Despite recent refactoring, these modules still exceed our 200-line target:

| File | Lines | Notes |
|------|-------|-------|
| `ui/display_utils.py` | 484 | Display formatting utilities |
| `database/event_store.py` | 483 | Central data store - may be acceptable |
| `database/repositories/metrics_repository.py` | 434 | Metrics calculations |
| `cli/branch.py` | 391 | **Single function is 295 lines!** |
| `config/config.py` | 386 | Configuration management |
| `core/conductor.py` | 378 | Core conversation orchestration |
| `metrics/calculators/flat_calculator.py` | 370 | Metrics computation |
| `core/rate_limiter.py` | 365 | Rate limiting logic |

**Note:** Some of these (like `event_store.py`) may be justifiably large as central architectural components.

### 2. The Monster `branch()` Function
- **File:** `cli/branch.py`, lines 50-342
- **Issue:** Single 295-line function handling multiple responsibilities
- **Proposed Fix:**
  ```python
  # Split into:
  class BranchValidator:
      def validate_agents()
      def validate_config()
  
  class BranchConfigBuilder:
      def build_from_params()
      def apply_defaults()
  
  class BranchExecutor:
      def execute_branch()
      def display_results()
  ```

### 3. Excessive Function Parameters
- **File:** `cli/run.py`
- **Issue:** `run()` function has 23 parameters
- **Proposed Fix:** Create `RunConfig` dataclass

## High Priority Issues

### 4. Generic Exception Handling
- **Scope:** 68 instances across 40 files
- **Pattern:** `except Exception as e:` without context
- **Fix:** Add specific exception types and error context

### 5. Inconsistent Error Handling
- **Issue:** Mixed approaches between `display.error()`, exceptions, and logging
- **Fix:** Create centralized `CLIErrorHandler` class

### 6. Missing Type Hints
- **Affected:** Most CLI modules
- **Priority Files:**
  - `cli/info.py`
  - `cli/stop.py`
  - `cli/monitor.py`

## Medium Priority Issues

### 7. Function-Level Imports
- **File:** `cli/branch.py` (lines 263, 264, 311, 382)
- **Fix:** Move imports to module level

### 8. Complex Nested Conditionals
- **Affected:** Multiple CLI modules
- **Fix:** Extract methods or use command pattern

### 9. Code Duplication
- **Pattern:** `display.error()` and `display.info()` repeated across 10+ files
- **Fix:** Create `CLIDisplay` mixin

## Low Priority Issues

### 10. Style Inconsistencies
- Mixed string formatting (f-strings vs .format())
- Inconsistent comment styles
- Magic numbers without constants

## Refactoring Strategy

### Phase 1: Critical Structure (Week 1)
1. Refactor `branch.py` - highest priority
2. Create shared CLI utilities
3. Add `CLIErrorHandler` class

### Phase 2: Type Safety (Week 2)
1. Add type hints to all CLI entry points
2. Type annotate public APIs
3. Add mypy to CI pipeline

### Phase 3: Module Size (Week 3)
1. Evaluate if large modules can be split further
2. Consider if some modules (like `event_store.py`) should remain large
3. Extract calculation logic from repositories

### Phase 4: Exception Handling (Week 4)
1. Replace generic exceptions with specific types
2. Add error context throughout
3. Standardize logging patterns

## Metrics to Track

- Module size adherence (<200 lines target, <300 acceptable, <500 hard limit)
- Type coverage percentage
- Cyclomatic complexity scores
- Test coverage for refactored code

## Notes

- Some modules may justifiably exceed 200 lines if they're central architectural components
- Recent refactoring has already improved module organization significantly
- Focus on the most egregious violations first (branch.py)