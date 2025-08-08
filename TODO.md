# TODO

This document tracks remaining tasks for Pidgin development.

## IMMEDIATE PRIORITY - Bug Fixes & Testing

### 🚨 Critical Issues
- [ ] **Merge deserialization fix** - Branch `fix/event-deserialization-bug` ready to merge
- [ ] **Merge module refactoring** - Branch `refactor/module-splitting` has 3 completed refactorings
- [ ] **Improve test coverage** - Current tests only check imports, not functionality
  - Tests should actually run experiments and verify data flow
  - Add end-to-end tests that catch serialization/deserialization issues
  - Test actual provider interactions (with mocks)

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
- [ ] experiments/state_builder.py - 514 lines
- [ ] ui/display_utils.py - 484 lines
- [ ] database/event_store.py - 477 lines (architectural component - may stay large)
- [ ] database/metrics_repository.py - 434 lines
- [ ] config/config.py - 402 lines
- [ ] cli/branch.py - 391 lines
- [ ] core/conductor.py - 372 lines

Total: 13 modules remaining (down from 19)

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