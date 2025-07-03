# Pidgin Project TODO

Last Updated: July 3, 2025

## Overview

This document tracks the ongoing refactoring and enhancement work for Pidgin. The goal is to create a clean, maintainable research tool for studying AI-to-AI conversation dynamics.

## ✅ Completed

- [x] **Remove dashboard entirely**
  - Deleted `pidgin/dashboard/` directory
  - Removed SharedState functionality
  - Simplified architecture significantly

- [x] **Remove unnecessary CLI commands**
  - Deleted `init`, `transcribe`, `report`, `compare` commands
  - Moved `stop-all` to `stop --all` flag
  - Removed `logs` command
  - Moved monitor to top-level

- [x] **Fix monitor command**
  - Removed SharedState dependencies
  - Now pulls from database only

- [x] **Conductor refactoring** *(Completed 2025-07-02)*
  - Split 852-line conductor.py into focused modules
  - Created: interrupt_handler.py, name_coordinator.py, turn_executor.py, message_handler.py, conversation_lifecycle.py
  - Preserved all event emissions exactly

- [x] **Add experiment completion notifications** *(Completed 2025-07-02)*
  - Added terminal bell (`\a`) for experiments in debug mode
  - Created notify.py module with cross-platform desktop notifications
  - Added --notify flag to chat command
  - Created comprehensive `pidgin experiment status` command with --watch and --notify

- [x] **Simplify chat display** *(Completed previously)*
  - Added --quiet and --verbose flags for display control
  - Panels already removed from regular messages
  - Color/prefixes used for speaker separation

- [x] **Switch from SQLite to DuckDB** *(Completed 2025-07-03)*
  - Created AsyncDuckDB wrapper with connection pooling
  - Implemented async storage layer with event sourcing
  - Database auto-creates with new schema on first use
  - Created comprehensive migration guide
  - Simplified schema to work with current DuckDB limitations

- [x] **Remove unnecessary db commands** *(Completed 2025-07-03)*
  - Removed `pidgin db` command group entirely
  - Integrated database stats into `pidgin monitor`
  - Updated documentation to reflect simpler approach

- [x] **Complete token counting implementation** *(Completed 2025-07-03)*
  - Added TokenUsageHandler to store token data in DuckDB
  - Enhanced TokenUsageEvent with prompt/completion token breakdown
  - Added get_last_usage() to xAI provider (others already had it)
  - Integrated token costs into system monitor
  - Added pricing data for all providers
  - Token usage now properly stored and tracked

- [x] **Documentation cleanup** *(Completed 2025-07-03)*
  - Removed duplicate README and ARCHITECTURE files from /docs
  - Deleted outdated migration documentation
  - Removed historical dashboard documentation
  - Removed redundant db-schema.txt (schema.py is source of truth)
  - Updated all references to match current implementation

- [x] **Cost calculation & provider pricing** *(Completed 2025-07-03)*
  - Implemented TokenUsageHandler to store token data in DuckDB
  - Added pricing data for all providers in token_handler.py
  - Integrated cost calculation in system monitor
  - Tracks cumulative costs per experiment

- [x] **Reorganize model configurations** *(Completed 2025-07-03)*
  - Moved model definitions to their respective provider files
  - Central config/models.py now aggregates from all providers
  - Makes provider updates self-contained
  - No functional changes, just better code organization

## 🚧 In Progress

### 🚨 Priority 1: Fix Event Storage Data Flow

**Current Problems:**
- Events are double-written to both events.jsonl files AND intended for DuckDB
- EventBus writes to jsonl files (event_bus.py lines 97-99)
- DuckDB has an `events` table schema but raw events aren't being stored there
- Only metrics and processed data go to DuckDB currently
- This creates confusion about source of truth and wastes disk I/O

**Proposed Solution:**
1. Modify EventBus to write events to DuckDB instead of jsonl files
2. Use the existing `events` table schema in schema.py
3. Ensure event replay functionality works from DuckDB
4. Remove jsonl file writing code
5. Update any code that reads from jsonl files to read from DuckDB

**Technical Details:**
- EventBus.__init__ takes event_log_path parameter (currently used for jsonl)
- Need to pass AsyncExperimentStore to EventBus instead
- Events should go to the `events` table with proper conversation_id and experiment_id
- Consider backward compatibility for existing jsonl files (migration tool?)
- EventBus is created in conversation_lifecycle.py line 68
- Event writing happens in event_bus.py _write_event() method

**Benefits:**
- Single source of truth for all events
- Better query performance for analysis
- Reduced disk I/O (no double writes)
- Cleaner architecture
- Event replay still possible via SQL queries

**Open Questions:**
- Should we keep jsonl as optional backup/export format?
- How to handle existing jsonl files from previous runs?
- Should event replay be synchronous or async?

## 📋 Upcoming Tasks


### 🔥 Priority 2: Documentation & CLI Cleanup


- [ ] **Update all documentation**
  - ✓ Update ARCHITECTURE.md SQLite references to DuckDB (completed)
  - Remove any remaining dashboard references
  - Update command examples
  - Document new architecture

### 🛠️ Priority 3: Core Functionality

- [ ] **Pattern detection enhancements**
  - Implement gratitude spiral detection
  - Add more conversation pattern recognizers


### 📊 Priority 4: Analysis Infrastructure

- [ ] **Auto-generated Jupyter notebooks**
  - Generate automatically when experiments/chats complete
  - Pre-populated with data and basic visualizations
  - Save alongside transcripts and logs

- [ ] **Data enrichment pipeline**
  - Lazy loading of expensive operations
  - Sentiment analysis, embeddings, etc.
  - Only run when requested via GraphQL/notebook

- [ ] **GraphQL interface for analysis**
  - Launch with `pidgin analyze --serve`
  - Flexible querying for researchers
  - Automatic enrichment on query
  - Replace complex CLI interactions

- [ ] **Post-hoc corpus creation**
  - Allow cherry-picking conversations for analysis
  - Create virtual experiments from existing data

## 🚫 Not Doing

These items have been explicitly decided against:

- **Real-time dashboards** - Adds complexity without sufficient value
- **Live experiment monitoring** - Static status commands are sufficient  
- **Separate enrichment commands** - Will be handled transparently via GraphQL
- **Analysis command group** - Current commands were deleted, future analysis via notebooks/GraphQL

## Architecture Notes

### Event System
- All events must be preserved during refactoring
- Analysis depends on complete event streams
- No hidden state outside of events

### Provider System  
- Providers remain agnostic (API vs local)
- Clean abstraction boundaries
- Model configs will move to provider files

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

## Questions for Future Discussion

1. **Notification implementation details** - Which libraries/methods for desktop notifications?
2. **GraphQL schema design** - What queries do researchers need most?
3. **Notebook template design** - What visualizations are most useful?
4. **Email notification service** - Build in-house or use external service?

---

This is a living document. Update it as tasks are completed or priorities change.