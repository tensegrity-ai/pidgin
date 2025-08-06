# TODO

This document tracks remaining tasks for Pidgin development.

## High Priority - Code Quality

### ✅ Large Module Refactoring - COMPLETED
**Goal**: Bring all modules under 200 lines per CLAUDE.md guidelines
**Progress**: All 6 critical modules completed! (see PLANS/large-module-refactoring.md)

**✅ Completed (2025-08-05)**:
- [x] database/schema.py - 651 → 42 lines (extracted to SQL files)
- [x] ui/display_filter.py - 637 → 137 lines (split into handlers)
- [x] io/event_deserializer.py - 580 → 235 lines (split by event type)
- [x] experiments/manager.py - 584 → 173 lines (split into 5 modules)
- [x] database/import_service.py - 563 → 188 lines (split into 4 modules)
- [x] cli/run.py - 454 → 192 lines (split into 5 handler modules)

**Medium Priority (>300 lines)**:
- [ ] analysis/notebook_cells.py - 540 lines
- [ ] database/transcript_formatter.py - 522 lines
- [ ] ui/tail_display.py - 520 lines
- [ ] experiments/state_builder.py - 514 lines
- [ ] ui/display_utils.py - 484 lines
- [ ] database/event_store.py - 477 lines (architectural component)
- [ ] database/metrics_repository.py - 434 lines
- [ ] config/config.py - 402 lines
- [ ] cli/branch.py - 391 lines
- [ ] core/conductor.py - 372 lines

Total: 16 modules remaining (down from 19)

## Medium Priority - Quality of Life

### Output Directory Organization
- [ ] Consider flattening experiment directory structure (single directory per experiment)
- [ ] Review if all generated files are necessary

## Low Priority - Nice to Have

### Documentation Updates
- [ ] Update examples to reflect best practices
- [ ] Add troubleshooting guide for common issues
- [ ] Document context limit behavior
- [ ] Update CHANGELOG.md with recent changes

### Testing & Validation
- [ ] Add tests for context limit handling
- [ ] Verify all providers handle errors consistently
- [ ] Test migration path for existing users
- [ ] Add integration tests for post-processing pipeline

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

## Recently Completed (2025-08-05)

**Module Refactoring (Phase 1 & partial Phase 2)**:
- ✅ Refactored database/schema.py from 651 to 42 lines (extracted SQL to .sql files)
- ✅ Refactored ui/display_filter.py from 637 to 137 lines (split into handler modules)
- ✅ Refactored io/event_deserializer.py from 580 to 235 lines (split by event type)
- ✅ Created comprehensive refactoring plan in PLANS/large-module-refactoring.md

**Previous completions**:
- ✅ Fixed post-processing chain (missing ManifestManager methods)
- ✅ Refactored monitor.py from 928 lines to 137 lines (split into 8 modules)
- ✅ Fixed token display in monitor
- ✅ Updated ARCHITECTURE.md to reflect current system
- ✅ Cleaned up outdated documentation files