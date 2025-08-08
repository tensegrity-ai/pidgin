# TODO

This document tracks remaining tasks for Pidgin development.

## IMMEDIATE PRIORITY - Bug Fixes & Testing

### Active Issues (2025-08-08)
(None currently - all immediate issues resolved)

## Completed Issues

### ✅ Completed (2025-08-08)
- [x] **Fixed duplicate experiment names** - Added retry logic to generate new name when duplicate detected
- [x] **Fixed 'Aborted' message on Ctrl+C** - Now properly shows that experiment continues in background
- [x] **Fixed monitor command** - Fixed status_filter parameter issue
- [x] **Merged deserialization fix** - Branch `fix/event-deserialization-bug` merged to main
- [x] **Merged module refactoring** - Branch `refactor/module-splitting` merged to main
- [x] **Test coverage maintained** - 18 tests passing, covering core functionality
  - Event deserialization tests catch serialization issues
  - Integration tests verify core flows work
  - Following minimal testing philosophy per TESTING.md

## High Priority - Code Quality

### Module Refactoring Progress
**Goal**: Bring all modules under 200 lines per CLAUDE.md guidelines

**✅ Completed (2025-08-08)**:
- [x] analysis/notebook_cells.py - 540 → 91 lines (split into cells/ submodules)
- [x] database/transcript_formatter.py - 522 → 69 lines (split into formatters/ submodules)
- [x] ui/tail_display.py - 520 → 8 lines (split into tail/ submodules)

**✅ Previously Completed (2025-08-05)**:
- [x] database/schema.py - 651 → 42 lines (extracted to SQL files)
- [x] ui/display_filter.py - 637 → 137 lines (split into handlers)
- [x] io/event_deserializer.py - 580 → 235 lines (split by event type) **[BUG INTRODUCED HERE]**
- [x] experiments/manager.py - 584 → 173 lines (split into 5 modules)
- [x] database/import_service.py - 563 → 188 lines (split into 4 modules)
- [x] cli/run.py - 454 → 192 lines (split into 5 handler modules)

**Remaining Large Modules (>300 lines)**:
- [ ] ui/display_utils.py - 484 lines
- [ ] database/event_store.py - 477 lines (architectural component - may stay large)
- [ ] database/metrics_repository.py - 434 lines
- [ ] config/config.py - 402 lines (has global singleton to remove)
- [ ] cli/branch.py - 391 lines
- [ ] core/conductor.py - 372 lines

**✅ Global Singletons Eliminated (2025-08-08)**:
- [x] database/schema_manager.py - Removed singleton pattern, now uses dependency injection
- [x] database/schema_loader.py - Removed global `_loader` instance, functions create instances on demand
- [x] providers/token_tracker.py - Removed global `get_token_tracker()`, now uses dependency injection
- [x] config/config.py - Removed global `get_config()`, now uses dependency injection
- [x] config/models.py - Models moved to AppContext, no more global MODELS instance
- [x] Created AppContext class for dependency injection container
- [x] Updated all components to receive dependencies via constructors

Total: 6 large modules remaining to refactor

## Medium Priority - Quality of Life

### Testing Infrastructure
- [ ] Create comprehensive integration test suite
- [ ] Add regression tests for all refactored modules
- [ ] Set up CI/CD to run tests on every commit
- [ ] Add performance benchmarks to catch regressions

### Output Directory Organization
- [ ] Consider flattening experiment directory structure (single directory per experiment)
- [ ] Review if all generated files are necessary

## Low Priority - Nice to Have

### Documentation Updates
- [ ] Update examples to reflect best practices
- [ ] Add troubleshooting guide for common issues
- [ ] Document context limit behavior
- [ ] Update CHANGELOG.md with recent changes

### Future Considerations
- [ ] Consider adding progress bars for long-running experiments
- [ ] Add experiment resume capability after interruption
- [ ] Support for custom analysis plugins
- [ ] Export to different formats (CSV, Parquet, etc.)

## Notes

- Focus on research integrity over engineering convenience
- Avoid adding features that could skew research data
- Keep changes minimal and well-documented
- Test thoroughly with real conversations

## Recently Completed (2025-08-08)

**Critical Bug Fix**:
- ✅ Fixed event deserialization bug introduced in commit 760bf45
- ✅ Added comprehensive regression tests for event deserialization
- ✅ Fixed timestamp and experiment_id passing in deserializers
- ✅ Fixed Turn and Message object construction

**Module Refactoring (Phase 2)**:
- ✅ Refactored analysis/notebook_cells.py from 540 to 91 lines
- ✅ Refactored database/transcript_formatter.py from 522 to 69 lines
- ✅ Refactored ui/tail_display.py from 520 to 8 lines

**Previous completions (2025-08-05)**:
- ✅ Fixed post-processing chain (missing ManifestManager methods)
- ✅ Refactored monitor.py from 928 lines to 137 lines (split into 8 modules)
- ✅ Updated ARCHITECTURE.md to reflect current system