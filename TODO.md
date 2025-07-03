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
  - Added database migration CLI commands (db migrate, status, reset)
  - Created comprehensive migration guide
  - Simplified schema to work with current DuckDB limitations

## 🚧 In Progress

- [ ] **Complete token counting implementation**
  - Track retry count from provider retry logic
  - Get token rate limits from provider config
  - Calculate actual usage rate over time
  - Fix OpenAI streaming API usage data capture

## 📋 Upcoming Tasks


### 🔥 Priority 2: Documentation & CLI Cleanup

- [ ] **Fix documentation about parallelization**
  - Update README to clarify sequential execution by default
  - Note architecture supports parallelism but practical constraints require sequential
  - Remove references to deleted commands

- [ ] **Update all documentation**
  - Remove dashboard references throughout
  - Update command examples
  - Document new architecture

### 🛠️ Priority 3: Core Functionality

- [ ] **Cost calculation & provider pricing**
  - Implement cost calculation in system monitor
  - Add provider pricing configurations
  - Track cumulative costs per experiment

- [ ] **Reorganize model configurations**
  - Move model definitions to their respective provider files
  - Keep aggregation and utilities in `/config/models.py`
  - Makes provider updates self-contained

- [ ] **Pattern detection enhancements**
  - Implement gratitude spiral detection
  - Add more conversation pattern recognizers

- [ ] **Complete experiment runner**
  - Implement conversation running logic in runner.py
  - Handle parallel execution properly

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