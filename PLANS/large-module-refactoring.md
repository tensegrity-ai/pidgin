# Large Module Refactoring Plan

This document outlines the refactoring strategy for modules exceeding the 200-line guideline established in CLAUDE.md.

## Overview

Per CLAUDE.md guidelines:
- **Ideal**: <200 lines (strive for this)
- **Acceptable**: <300 lines
- **Hard limit**: <500 lines (must refactor if exceeded)

**Status**: Phase 1 complete, Phase 2 partially complete (3 of 6 critical modules refactored)

## Priority 1: Critical Modules (>600 lines)

### 1. ✅ database/schema.py (651 → 42 lines) - COMPLETED
**Refactored Into**:
- `database/schemas/` directory with 9 SQL files
- `database/schema_loader.py` (125 lines) - Dynamic SQL loader
- Main module now just 42 lines with backward compatibility

**Result**: Clean separation, SQL syntax highlighting, maintained all functionality

### 2. ✅ ui/display_filter.py (637 → 137 lines) - COMPLETED
**Refactored Into**:
- `ui/display_filter.py` (137 lines) - Main routing class
- `ui/display_handlers/base.py` (82 lines) - Shared utilities
- `ui/display_handlers/conversation.py` (177 lines) - Conversation lifecycle
- `ui/display_handlers/messages.py` (83 lines) - Message display
- `ui/display_handlers/errors.py` (185 lines) - Error handling
- `ui/display_handlers/system.py` (106 lines) - System events

**Result**: All modules under 200 lines, clear separation by event type

## Priority 2: High Priority (500-600 lines)

### 3. ✅ experiments/manager.py (584 → 173 lines) - COMPLETED
**Refactored Into**:
- `experiments/manager.py` (173 lines) - Core manager interface
- `experiments/experiment_resolver.py` (139 lines) - ID resolution and discovery
- `experiments/daemon_manager.py` (216 lines) - Start/stop daemon processes
- `experiments/experiment_status.py` (138 lines) - Status checking and listing
- `experiments/process_launcher.py` (239 lines) - Process launching utilities

**Result**: Clear separation of responsibilities, all modules near 200-line target

### 4. ✅ io/event_deserializer.py (580 → 235 lines) - COMPLETED
**Refactored Into**:
- `io/event_deserializer.py` (235 lines) - Main routing and legacy support
- `io/deserializers/base.py` (48 lines) - Shared timestamp parsing
- `io/deserializers/conversation.py` (180 lines) - Conversation events
- `io/deserializers/message.py` (96 lines) - Message events
- `io/deserializers/error.py` (58 lines) - Error events
- `io/deserializers/system.py` (76 lines) - System events

**Result**: Clean separation by event category, easier to extend

### 5. ✅ database/import_service.py (563 → 188 lines) - COMPLETED
**Refactored Into**:
- `database/import_service.py` (188 lines) - Main import orchestration
- `database/importers/conversation_importer.py` (174 lines) - Import conversation data
- `database/importers/metrics_importer.py` (161 lines) - Import metrics data
- `database/importers/event_processor.py` (149 lines) - Process JSONL events

**Result**: Each importer is focused and under 200 lines, clearer data flow

## Priority 3: Medium Priority (400-500 lines)

### 6. ✅ cli/run.py (454 → 192 lines) - COMPLETED
**Refactored Into**:
- `cli/run.py` (192 lines) - Main command definition
- `cli/run_handlers/command_handler.py` (175 lines) - Main command logic
- `cli/run_handlers/setup.py` (149 lines) - Setup and validation logic
- `cli/run_handlers/execution.py` (129 lines) - Execution logic
- `cli/run_handlers/spec_handler.py` (69 lines) - YAML spec handling

**Result**: Clean separation of concerns, all modules under 200 lines

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

## Implementation Progress

### ✅ Phase 1: Quick Wins - COMPLETED
1. **database/schema.py** - ✅ Moved SQL to .sql files (651 → 42 lines)
2. **ui/display_filter.py** - ✅ Split by event type (637 → 137 lines)

### ✅ Phase 2: Core Refactoring - COMPLETED
3. **io/event_deserializer.py** - ✅ Split by event category (580 → 235 lines)
4. **experiments/manager.py** - ✅ Split into 5 modules (584 → 173 lines)
5. **database/import_service.py** - ✅ Split into 4 modules (563 → 188 lines)

### ✅ Phase 3: CLI Cleanup - COMPLETED
6. **cli/run.py** - ✅ Split into 5 handler modules (454 → 192 lines)

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