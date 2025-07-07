# Pidgin Project TODO

Last Updated: July 6, 2025

## Overview

This document tracks the ongoing refactoring and enhancement work for Pidgin. The goal is to create a clean, maintainable research tool for studying AI-to-AI conversation dynamics.

**MAJOR UPDATE**: Comprehensive code audit completed on July 6, 2025. See CODE_AUDIT_REPORT.md for full details.

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
- [x] **Create comprehensive test suite** ✅ IN PROGRESS
  - Fixed 238 tests (up from 181 broken tests)
  - Created test builders for consistent test data
  - Achieved high coverage on core modules:
    - MetricsCalculator: 97% coverage (20 tests)
    - InterruptHandler: 88% coverage (13 tests) 
    - Router: 93% coverage (13 tests)
    - TurnExecutor: 100% coverage (11 tests)
    - EventRepository: 76% coverage
    - ExperimentRepository: 91% coverage
    - ConversationRepository: 93% coverage
    - MessageRepository: 85% coverage
    - MetricsRepository: 89% coverage
  - Still need tests for: name_coordinator, context_manager, event_wrapper, token_handler
  - Add integration tests for concurrent operations

### Thread Safety Issues 🚨
- [ ] **Add asyncio locks to shared state**
  - EventBus._jsonl_files dict
  - ManifestManager operations
  - EventHandler conversation state dicts
  - 14 modules identified with issues

### God Object Refactoring 🚨
- [x] **Split EventStore (856 lines, 22 methods)** ✅ DONE
  - Created BaseRepository with retry logic
  - Created EventRepository (76% coverage)
  - Created ExperimentRepository (91% coverage)
  - Created ConversationRepository (93% coverage)
  - Created MessageRepository (85% coverage)
  - Created MetricsRepository (89% coverage)
  - Maintained backward compatibility

- [ ] **Refactor MetricsCalculator (437 lines, 21 methods)**
  - Separate calculation from analysis
  - Extract formatting to separate module

## Priority 2: High Priority Code Quality Issues

### Code Duplication
- [ ] **Extract provider base functionality**
  - Error handling (anthropic.py:96-114, openai.py:189-205)
  - Context truncation (3+ providers)
  - Create shared error mapping utility

### Long Methods
- [ ] **Refactor conductor.run_conversation() (142 lines)**
- [ ] **Refactor message_handler.get_agent_message() (152 lines)**
- [ ] **Refactor experiment_runner._run_single_conversation() (134 lines)**
- [ ] **Refactor event_store.import_experiment() (104 lines)**

### Inconsistent Error Handling
- [ ] **Standardize Google provider error handling**
- [ ] **Fix bare except clauses**
  - cli/helpers.py:105-110
  - Multiple async_duckdb.py locations

## Priority 3: Fix Critical Issues from Code Audit (Original)

### Database Issues
- [ ] **Fix race condition in event sequences** (event_store.py:138-145)
  - Make sequence generation atomic with INSERT
  - Impact: Data corruption with concurrent writes
  
- [ ] **Fix database connection leaks** (async_duckdb.py)
  - Properly close connections in all worker threads
  - Add connection timeout configuration
  
- [ ] **Add transaction boundaries**
  - Wrap multi-table operations in transactions
  - Prevent partial updates on failure

### Memory Leaks
- [x] **Event history unbounded growth** (EventBus.event_history) [DONE]
  - Added max_history_size limit (default: 1000)
  - Automatically prunes old events when limit exceeded
  
- [ ] **JSONL file handle leaks** (event_bus.py)
  - Close files after each conversation
  - Implement file handle pooling
  
- [ ] **Message history accumulation**
  - Add message pruning for long conversations
  - Archive old messages to disk

### Resource Management
- [x] **Provider cleanup** [DONE]
  - Added `async def cleanup()` method to base Provider
  - Providers can now override to close connections properly
  
- [ ] **Thread pool management**
  - Ensure ThreadPoolExecutor shutdown in all cases
  - Add proper cleanup in daemon processes

## Priority 4: Medium Priority Code Quality Issues

### Magic Strings/Numbers
- [ ] **Create comprehensive constants module**
  - 250+ hardcoded status strings
  - Extract all magic values
  - Enforce usage across codebase

### Naming Consistency
- [ ] **Standardize naming conventions**
  - Use full names: conversation (not conv), experiment (not exp)
  - Consistent agent naming: agent_a everywhere
  - Update all 127 files with mixed naming

### Missing Validation
- [ ] **Add convergence weight validation**
  - Ensure weights sum to 1.0
  - Add config value schema validation
  - Validate all user inputs

### API Key Management
- [ ] **Centralize credential management**
  - Create secure credential store
  - Remove direct env var access from providers
  - Consider keyring integration

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

## [WIP] Priority 6: Performance Optimizations

### Metrics Calculator
- [ ] **Cache tokenization results** - Avoid redundant processing
- [ ] **Fix O(n²) algorithms** - Optimize n-gram operations
- [ ] **Add input validation** - Prevent crashes on edge cases
- [ ] **Fix division by zero risks** - Add proper guards

### Database Performance
- [ ] **Add missing indexes** for common queries
- [ ] **Remove schema checks on every insert**
- [ ] **Implement connection pooling**
- [ ] **Optimize batch processing**

## Priority 7: Analysis Infrastructure

### Features to Build
- [ ] **Auto-generated Jupyter notebooks**
  - Generate automatically when experiments complete
  - Pre-populated with data and basic visualizations
  - Save alongside transcripts and logs

- [ ] **GraphQL interface for analysis**
  - Launch with `pidgin analyze --serve`
  - Flexible querying for researchers
  - Automatic enrichment on query

- [ ] **Pattern detection enhancements**
  - Implement gratitude spiral detection
  - Add more conversation pattern recognizers

## [DONE] Recently Completed

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
- [ ] **Remove orphaned files**
  - Delete nested pidgin_output/experiments/pidgin_output/
  - Remove banner_options.txt
  - Clean up debug_output.txt
  - Add .DS_Store to .gitignore

### Minor Code Issues
- [ ] **Address 5 TODO comments**
  - token_handler.py:89-91 (config from provider)
  - conversation_lifecycle.py:346 (gather metrics)
  - event_handler.py:384 (gratitude spiral detection)
  - event_wrapper.py:94 (track retry count)

- [ ] **Remove unused ConversationError exception**
- [ ] **Document Router Protocol purpose or remove**

## Quick Wins (Easy Fixes with High Impact)

1. **Create initial test files** - Start test suite foundation (2 hours)
2. **Add asyncio locks to EventBus** - Fix critical thread safety (1 hour)
3. **Extract provider error constants** - Reduce duplication (2 hours)
4. **Split long methods in conductor.py** - Improve maintainability (3 hours)
5. **Create constants.py with status strings** - Reduce magic strings (2 hours)
6. **Fix bare except in helpers.py** - Better error handling (30 min)
7. **Add convergence weight validation** - Prevent invalid configs (1 hour)

---

This is a living document. Update it as tasks are completed or priorities change.