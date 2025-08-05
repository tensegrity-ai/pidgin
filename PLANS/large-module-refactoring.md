# Large Module Refactoring Plan

This document outlines the refactoring strategy for modules exceeding the 200-line guideline established in CLAUDE.md.

## Overview

Per CLAUDE.md guidelines:
- **Ideal**: <200 lines (strive for this)
- **Acceptable**: <300 lines
- **Hard limit**: <500 lines (must refactor if exceeded)

Current state: ~19 modules need refactoring, with 6 critical modules over 500 lines.

## Priority 1: Critical Modules (>600 lines)

### 1. database/schema.py (651 lines)
**Current Structure**: 
- 8 SQL schema definitions as large multiline strings
- 2 helper functions

**Refactor Into**:
- `database/schemas/conversation_turns.sql` - CONVERSATION_TURNS_SCHEMA
- `database/schemas/events.sql` - EVENT_SCHEMA  
- `database/schemas/experiments.sql` - EXPERIMENTS_SCHEMA
- `database/schemas/conversations.sql` - CONVERSATIONS_SCHEMA
- `database/schemas/turn_metrics.sql` - TURN_METRICS_SCHEMA
- `database/schemas/messages.sql` - MESSAGES_SCHEMA
- `database/schemas/token_usage.sql` - TOKEN_USAGE_SCHEMA
- `database/schemas/context_truncations.sql` - CONTEXT_TRUNCATIONS_SCHEMA
- `database/schema_loader.py` - Load SQL files and provide helper functions

**Benefits**: Clean separation, SQL files can be syntax-highlighted, easier to maintain

### 2. ui/display_filter.py (637 lines)
**Current Structure**: 
- 1 class with 18 methods handling different event displays

**Refactor Into**:
- `ui/display_filter.py` (~150 lines) - Main class with routing logic
- `ui/display_handlers/conversation.py` - Start/end/resume handlers
- `ui/display_handlers/messages.py` - Message/turn complete handlers  
- `ui/display_handlers/errors.py` - Error/timeout/context limit handlers
- `ui/display_handlers/system.py` - System prompt, pacing, token usage handlers

**Benefits**: Each handler module focuses on specific event types, easier testing

## Priority 2: High Priority (500-600 lines)

### 3. experiments/manager.py (584 lines)
**Current Structure**: 
- 1 class with 12 methods managing experiments

**Refactor Into**:
- `experiments/manager.py` (~200 lines) - Core manager interface
- `experiments/experiment_resolver.py` - ID resolution and discovery
- `experiments/daemon_manager.py` - Start/stop daemon processes
- `experiments/experiment_status.py` - Status checking and listing

**Benefits**: Clear separation of responsibilities, reusable components

### 4. io/event_deserializer.py (580 lines)
**Current Structure**: 
- 1 class with 24 deserialization methods

**Refactor Into**:
- `io/event_deserializer.py` (~150 lines) - Main deserializer with routing
- `io/deserializers/conversation.py` - Conversation event builders
- `io/deserializers/message.py` - Message event builders
- `io/deserializers/error.py` - Error event builders
- `io/deserializers/system.py` - System event builders

**Benefits**: Parallel structure to display handlers, easier to add new event types

### 5. database/import_service.py (563 lines)
**Current Structure**: 
- 1 class with 11 methods for importing data

**Refactor Into**:
- `database/import_service.py` (~150 lines) - Main import orchestration
- `database/importers/conversation_importer.py` - Import conversation data
- `database/importers/metrics_importer.py` - Import metrics data
- `database/importers/event_importer.py` - Import events

**Benefits**: Each importer can be optimized independently, clearer data flow

## Priority 3: Medium Priority (400-500 lines)

### 6. cli/run.py (454 lines)
**Current Structure**: 
- Single Click command with many options

**Refactor Into**:
- `cli/run.py` (~150 lines) - Main command definition
- `cli/run_handlers/setup.py` - Setup and validation logic
- `cli/run_handlers/execution.py` - Execution logic
- `cli/run_handlers/display.py` - Display configuration

**Benefits**: Easier to test CLI logic, cleaner command definition

## Other Notable Modules (300-400 lines)

These should also be refactored but are lower priority:
- `analysis/notebook_cells.py` (540 lines)
- `database/transcript_formatter.py` (522 lines)
- `ui/tail_display.py` (520 lines)
- `experiments/state_builder.py` (514 lines)
- `ui/display_utils.py` (484 lines)
- `database/event_store.py` (477 lines)
- `database/metrics_repository.py` (434 lines)
- `config/config.py` (402 lines)
- `cli/branch.py` (391 lines)
- `core/conductor.py` (372 lines)

## Implementation Strategy

### Phase 1: Quick Wins
1. **database/schema.py** - Simply move SQL to .sql files
2. **ui/display_filter.py** - Clear event type boundaries

### Phase 2: Core Refactoring
3. **io/event_deserializer.py** - Similar pattern to display_filter
4. **experiments/manager.py** - Well-defined functional boundaries
5. **database/import_service.py** - Clear data type boundaries

### Phase 3: CLI Cleanup
6. **cli/run.py** - Requires careful handling of Click decorators

## Testing Strategy

For each refactored module:
1. Write integration tests for the original monolithic module
2. Refactor into smaller modules
3. Ensure integration tests still pass
4. Add unit tests for new individual modules
5. Remove original monolithic module

## Success Metrics

- All modules under 200 lines (ideal) or at most 300 lines (acceptable)
- No loss of functionality
- Improved test coverage
- Faster test execution (smaller test scopes)
- Easier navigation and maintenance

## Timeline Estimate

- Phase 1: 2-3 hours
- Phase 2: 4-6 hours  
- Phase 3: 2-3 hours
- Total: ~1-2 days of focused work

## Notes

- Special exemption for EventStore (477 lines) as it's a central architectural component
- Focus on maintaining clear interfaces between modules
- Preserve all existing functionality
- Document any API changes in CHANGELOG.md