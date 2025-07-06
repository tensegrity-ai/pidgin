# Pidgin Project TODO

Last Updated: July 5, 2025

## Overview

This document tracks the ongoing refactoring and enhancement work for Pidgin. The goal is to create a clean, maintainable research tool for studying AI-to-AI conversation dynamics.

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

## Priority 1: Fix Critical Issues from Code Audit

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

## Priority 2: Complete Architecture Unification

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

## [WIP] Priority 4: Performance Optimizations

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

## Priority 5: Analysis Infrastructure

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

## Quick Wins (Easy Fixes with High Impact)

1. **Add shlex.quote() to notification commands** - Fixes critical security issue (30 min)
2. **Set max event history size** - Prevents memory leaks (1 hour)
3. **Add database connection timeout** - Improves reliability (1 hour)
4. **Cache tokenization results** - Significant performance boost (2 hours)
5. **Add input validation limits** - Prevents resource exhaustion (1 hour)

---

This is a living document. Update it as tasks are completed or priorities change.