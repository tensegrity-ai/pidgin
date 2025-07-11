# Pidgin Project TODO

Last Updated: July 9, 2025

## Overview

This document tracks the ongoing refactoring and enhancement work for Pidgin. The goal is to create a clean, maintainable research tool for studying AI-to-AI conversation dynamics.

**MAJOR UPDATE**: Comprehensive code audit completed on July 6, 2025. See CODE_AUDIT_REPORT.md for full details.
**UPDATE July 7, 2025**: Completed EventStore repository refactoring and all Priority 1-2 code quality issues.
**UPDATE July 9, 2025**: Completed constants module, API key management, Google error handling, and display system improvements.

## Priority 0: Critical Security Fixes (Immediate)

### [DONE] Command Injection Vulnerabilities (FIXED)
- **Location**: `pidgin/cli/notify.py` (lines 21-22, 36-37), `pidgin/cli/ollama_setup.py` (line 85-89)
- **Risk**: Arbitrary command execution through unsanitized inputs
- **Fix**: Use `shlex.quote()` or array-based subprocess calls
- **Impact**: HIGH - Could allow malicious code execution

### [DONE] Other Security Issues (FIXED)
- [DONE] Path traversal risks in output paths - Added validation
- [DONE] Missing input validation limits (turns, repetitions) - Added IntRange limits
- [DONE] Integer overflow possibilities - Bounded with reasonable limits

## Priority 1: Critical Issues from Code Audit (NEW)

### Test Suite Creation 🚨
- [x] **Create comprehensive test suite** ✅ DONE
  - Fixed 290 tests (up from 181 broken tests)
  - Created test builders for consistent test data
  - Overall coverage: 42% (up from 16%)
  - Achieved high coverage on core modules:
    - MetricsCalculator: 97% coverage (20 tests) - Exceeds 95% goal ✓
    - InterruptHandler: 88% coverage (13 tests) - Exceeds 85% goal ✓
    - Router: 93% coverage (13 tests) - Exceeds 90% goal ✓
    - TurnExecutor: 100% coverage (11 tests) - Exceeds 95% goal ✓
    - EventRepository: 76% coverage - Close to 80% goal
    - ExperimentRepository: 91% coverage - Exceeds 80% goal ✓
    - ConversationRepository: 93% coverage - Exceeds 80% goal ✓
    - MessageRepository: 85% coverage - Exceeds 80% goal ✓
    - MetricsRepository: 89% coverage - Exceeds 80% goal ✓
    - NameCoordinator: 100% coverage (14 tests) - Exceeds 80% goal ✓
    - MessageHandler: 98% coverage (17 tests) - Exceeds 80% goal ✓
    - EventBus: 89% coverage - Close to 90% goal
    - Types: 100% coverage - Exceeds 90% goal ✓
    - Conductor: 81% coverage - Exceeds 80% goal ✓
    - EventWrapper: 100% coverage - Exceeds 85% goal ✓
    - TokenHandler: 93% coverage - Exceeds 90% goal ✓
  - Test files exist for: name_coordinator, context_manager, event_wrapper, token_handler
  - Need to check coverage and completeness of existing test files
  - Add integration tests for concurrent operations

### Thread Safety Issues 🚨
- [x] **Add asyncio locks to shared state** ✅ DONE
  - EventBus._jsonl_files dict (has _jsonl_lock)
  - ManifestManager operations (has _lock)
  - EventHandler conversation state dicts (has _state_lock)
  - All critical modules now have proper thread safety

### God Object Refactoring 🚨
- [x] **Split EventStore (1358 lines → 250 lines)** ✅ DONE (July 7, 2025)
  - Created BaseRepository with common DB operations
  - Created EventRepository for event storage/retrieval (with atomic sequence generation)
  - Created ExperimentRepository for experiment CRUD  
  - Created ConversationRepository for conversation management
  - Created MessageRepository for message storage
  - Created MetricsRepository for metrics operations
  - Added SchemaManager for caching schema initialization
  - EventStore now a clean facade delegating to repositories (250 lines, 81% reduction)
  - Maintained full backward compatibility
  - Added comprehensive test suite (25 tests, all passing)

- [x] **Refactor MetricsCalculator (437 lines → 222 lines)** ✅ DONE
  - Split into 4 focused modules:
    - MetricsCalculator (orchestrator, 222 lines)
    - TextAnalyzer (text parsing, 101 lines)
    - ConvergenceCalculator (convergence metrics, 104 lines)
    - LinguisticAnalyzer (linguistic analysis, 97 lines)
  - Has 97% test coverage

## Priority 2: High Priority Code Quality Issues

### Code Duplication
- [x] **Extract provider base functionality** ✅ DONE (July 7, 2025)
  - [x] Error handling (anthropic.py:96-114, openai.py:189-205) - Created error_utils.py
  - [x] Create shared error mapping utility - ProviderErrorHandler with 100% coverage
  - [x] Context truncation (3+ providers) - Extracted to context_utils.py
  - [x] Update providers to use new error_utils module - All providers updated

### Long Methods
- [x] **Refactor conductor.run_conversation()** ✅ DONE (Already refactored to 58 lines)
- [x] **Refactor message_handler.get_agent_message()** ✅ DONE (Already refactored to 34 lines)
- [x] **Refactor experiment_runner._run_single_conversation()** ✅ DONE (Already refactored to 43 lines)
- [x] **Refactor _calculate_and_store_turn_metrics() (176 lines)** ✅ DONE (July 10, 2025)
  - Split into 4 focused methods: orchestration, data prep, agent metrics, SQL execution
  - Each method now has single responsibility

### Inconsistent Error Handling
- [x] **Standardize Google provider error handling** ✅ DONE (July 9, 2025)
  - Now uses standardized error_utils.py with ProviderErrorHandler
  - Consistent error messages across all providers
- [x] **Fix bare except clauses** ✅ DONE (July 10, 2025)
  - cli/helpers.py:105-110 now catches specific httpx exceptions
  - Note: async_duckdb.py no longer exists after repository refactoring
  - One bare except remains in readme_generator.py (needs fixing)

## Priority 3: Fix Critical Issues from Code Audit (Original)

### Database Issues
- [x] **Fix race condition in event sequences** ✅ DONE (July 7, 2025)
  - Made sequence generation atomic with INSERT in EventRepository
  - Impact: Data corruption with concurrent writes ELIMINATED
  
- [x] **Fix database connection leaks** ✅ DONE (July 7, 2025)
  - async_duckdb.py no longer exists after repository refactoring
  - Database connections now properly managed by repository pattern
  
- [x] **Add transaction boundaries** ✅ DONE (July 10, 2025)
  - ImportService already wraps operations in db.begin()/commit()
  - Prevents partial updates on failure

### Memory Leaks
- [x] **Event history unbounded growth** (EventBus.event_history) [DONE]
  - Added max_history_size limit (default: 1000)
  - Automatically prunes old events when limit exceeded
  
- [x] **JSONL file handle leaks** ✅ DONE (July 7, 2025)
  - Added close_conversation_log() call when conversations end
  - Files are now properly closed per conversation, not just on EventBus stop
  
- [x] **Message history accumulation** ✅ NOT NEEDED (July 9, 2025)
  - ProviderContextManager already handles context limits with smart truncation
  - Keeps system messages + sliding window of recent messages
  - Binary search algorithm maximizes messages within token limits
  - Full history preserved in JSONL files for analysis
  - In-memory list is not a concern for typical conversation lengths

### Resource Management
- [x] **Provider cleanup** [DONE]
  - Added `async def cleanup()` method to base Provider
  - Providers can now override to close connections properly
  
- [x] **Thread pool management** ✅ NOT APPLICABLE (July 10, 2025)
  - No ThreadPoolExecutor usage found in production code
  - Only appears in tests and outdated documentation
  - Database operations are synchronous, not async

## Priority 4: Medium Priority Code Quality Issues

### Magic Strings/Numbers
- [x] **Create comprehensive constants module** ✅ DONE (July 9, 2025)
  - Created 10-module constants package covering all domains
  - Extracted 250+ hardcoded strings into organized constants
  - Updated entire codebase to use constants
  - Modules: agents, conversations, events, experiments, files, linguistic, manifests, metrics, providers, symbols

### Naming Consistency
- [x] **Standardize naming conventions** ✓ COMPLETED 2025-01-10
  - Use full names: conversation (not conv), experiment (not exp)
  - Consistent agent naming: agent_a everywhere
  - Updated all files with mixed naming

### Missing Validation
- [x] **Add convergence weight validation** ✅ DONE (July 9, 2025)
  - Added _validate_convergence_weights() in config.py
  - Ensures weights sum to 1.0 (with floating point tolerance)
  - Set "structural" as default convergence profile
- [x] **Add config value schema validation** ✅ DONE (July 10, 2025)
  - Created comprehensive Pydantic models in config/schema.py
  - Validates all config values on load
  - Includes ConvergenceWeights and ConversationConfig models

### API Key Management
- [x] **Centralize credential management** ✅ DONE (July 9, 2025)
  - Created APIKeyManager class for centralized key management
  - All providers now use APIKeyManager.get_api_key()
  - Pre-experiment validation ensures keys exist before starting
  - Beautiful error panels guide users on missing keys

## Priority 5: Complete Architecture Unification

### [DONE] Unified `pidgin run` Command (COMPLETED)
- [DONE] Created unified run.py combining chat and experiment
- [DONE] Moved experiment subcommands to top level
- [DONE] Single conversations run in foreground by default
- [DONE] Multiple repetitions run as daemon by default
- [DONE] Deleted old chat.py and experiment.py files
- [DONE] Extracted models command to separate file
- [DONE] Updated all internal references

### [DONE] Remaining Unification Work (COMPLETED)
- [DONE] **Update documentation**
  - [DONE] Updated README with new command structure
  - [DONE] Updated all examples to use `pidgin run`
  - [DONE] Removed references to old commands

## [DONE] Priority 3: Fix Event Storage Data Flow (COMPLETED)

### Implemented JSONL-First Architecture:
- [DONE] JSONL files are now the single source of truth
- [DONE] Removed direct database writes during conversations
- [DONE] Created manifest.json for efficient state tracking
- [DONE] Built OptimizedStateBuilder with mtime caching
- [DONE] Added `pidgin import` command for batch loading to DuckDB
- [DONE] Eliminated database lock contention

### Benefits Achieved:
- No more lock conflicts during experiments
- Instant monitoring via manifest.json
- Standard Unix tools work (tail, grep, jq)
- Post-experiment analysis via DuckDB
- Clean separation of concerns

## [DONE] Priority 6: Performance Optimizations (July 10, 2025)

### Metrics Calculator ✅ DONE
- [x] **Cache tokenization results** - Added token cache in OptimizedMetricsCalculator
- [x] **Fix O(n²) algorithms** - Reduced cumulative overlap and repetition to O(n)
- [x] **Add division by zero guards** - Fixed unguarded divisions in display.py
- [x] **Optimize performance** - Created OptimizedMetricsCalculator with O(n) performance

### Database Performance ✅ COMPLETED (January 10, 2025)
- [x] **Add missing indexes** for common queries - Added 8 new indexes for query optimization
- [x] **Remove schema checks on every insert** - SchemaManager already implements caching
- [x] **Implement connection pooling** - Created ConnectionPool class with thread-safe pooling
- [x] **Optimize batch processing** - Replaced individual INSERTs with executemany() for better performance

## Priority 7: Analysis Infrastructure

### Features to Build
- [x] **Enhanced experiment output** ✅ DONE (July 10, 2025)
  - Experiment directories now use format: exp_id_name_date
  - Auto-generated README.md for each experiment
  - Improved experiment resolution by name/ID
  - Better organization for research workflows

- [x] **Auto-generated Jupyter notebooks** ✅ DONE (July 10, 2025)
  - Generates automatically when experiments complete
  - Pre-populated with convergence, vocabulary, and length analysis
  - Includes 6+ visualization types and statistical summaries
  - Saved as analysis.ipynb in experiment directories
  - Gracefully handles missing nbformat dependency

- [ ] **GraphQL interface for analysis**
  - Launch with `pidgin analyze --serve`
  - Flexible querying for researchers
  - Automatic enrichment on query

## [DONE] Recently Completed

### Experiment Organization Improvements (July 10, 2025)
- [DONE] Enhanced directory naming: exp_id_name_date format
- [DONE] Auto-generated README.md for each experiment
- [DONE] Improved experiment resolution supporting names and partial IDs
- [DONE] Fixed bare except clauses (except one in readme_generator.py)
- [DONE] Added Pydantic config validation schemas
- [DONE] Confirmed transaction boundaries already implemented

### Display System Improvements (July 9, 2025)
- [DONE] Enabled Rich logging for beautiful error formatting
- [DONE] Replaced all console.print() calls with display utilities
- [DONE] Enhanced experiment completion display with manifest data
- [DONE] Added rate limit pacing messages in panels
- [DONE] Fixed Google provider JSON serialization error
- [DONE] Consistent panel-based UI throughout application

### Directory Structure Consolidation (July 6, 2025)
- [DONE] Consolidated display/ into ui/ directory
- [DONE] Moved progress_panel.py from display/ to ui/
- [DONE] Moved local/ providers into providers/ directory
- [DONE] Moved ollama_helper.py and test_model.py to providers/
- [DONE] Updated all imports and module exports

### Display System Overhaul (July 5, 2025)
- [DONE] Created centered progress panel as default display
- [DONE] Added `--verbose` flag for live conversation view
- [DONE] Made `--quiet` run in background with notifications
- [DONE] Added real-time token usage and cost tracking
- [DONE] Implemented convergence trend indicators (↑, ↑↑, →, ↓, ↓↓)
- [DONE] Removed screen-like attach/detach behavior
- [DONE] Added process titles for daemons (pidgin-exp12345)

## Not Doing

These items have been explicitly decided against:
- **Real-time dashboards** - Adds complexity without sufficient value
- **Live experiment monitoring** - Static status commands are sufficient  
- **Complex visualizations** - Let researchers use their own tools
- **Separate enrichment commands** - Will be handled transparently via GraphQL
- **Screen-like attach/detach** - Use standard Unix tools instead

## Architecture Notes

### Event System
- All events must be preserved during refactoring
- Analysis depends on complete event streams
- No hidden state outside of events

### Provider System  
- Providers remain agnostic (API vs local)
- Clean abstraction boundaries
- Add proper cleanup methods

### Sequential Execution
- Default max_parallel = 1 due to rate limits and hardware constraints
- Architecture supports parallelism but reality requires sequential
- Document this clearly to set expectations

## Development Philosophy

From CLAUDE.md:
- Build only what's needed
- Present data, not narratives
- Use skeptical language
- Keep modules under 200 lines
- Methods under 50 lines

## Priority 8: Low Priority Issues

### Repository Cleanup
- [x] **Remove orphaned files** ✅ DONE (July 10, 2025)
  - Cleaned all __pycache__ directories and .pyc files
  - .DS_Store already in .gitignore
  - Note: Specific files mentioned may no longer exist

### Minor Code Issues
- [x] **Fix remaining bare except** ✅ DONE (Already fixed)
  - readme_generator.py now uses specific exception catching

- [x] **Fix outdated documentation** ✅ DONE (Already fixed)
  - database.md no longer mentions async operations or ThreadPoolExecutor
  - async_duckdb.py references already removed

- [x] **Address 4 TODO comments** ✅ DONE (July 10, 2025)
  - token_handler.py:89 - Now gets RPM from StreamingRateLimiter.DEFAULT_RATE_LIMITS
  - token_handler.py:91 - Clarified that RPM tracking is handled by StreamingRateLimiter
  - conversation_lifecycle.py:342 - Removed TODO, clarified transcripts saved via JSONL
  - event_wrapper.py:207 - Clarified retry tracking is internal to providers
  - event_handler.py:384 (gratitude spiral detection)
  - event_wrapper.py:94 (track retry count)

- [x] **Remove unused ConversationError exception** ✅ DONE (July 10, 2025)
- [x] **Document Router Protocol purpose** ✅ DONE (July 10, 2025)
  - Created docs/conversation-architecture.md explaining role transformation
  - Cleaned up docs/ directory and created index

## Quick Wins (All Completed! ✅)

1. **Create initial test files** - ✅ DONE
2. **Add asyncio locks to EventBus** - ✅ DONE
3. **Extract provider error constants** - ✅ DONE (created error_utils.py)
4. **Split long methods in conductor.py** - ✅ DONE (refactored into helper methods)
5. **Create constants.py with status strings** - ✅ DONE (comprehensive 10-module package)
6. **Fix bare except in helpers.py** - ✅ DONE (fixed httpx exceptions)
7. **Add convergence weight validation** - ✅ DONE (validates sum to 1.0)
8. **Centralize API key management** - ✅ DONE (created APIKeyManager)
9. **Enable Rich logging** - ✅ DONE (beautiful error formatting)
10. **Standardize Google error handling** - ✅ DONE (uses error_utils.py)

---

This is a living document. Update it as tasks are completed or priorities change.