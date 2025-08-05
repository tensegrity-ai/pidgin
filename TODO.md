# TODO

This document tracks remaining tasks for Pidgin development.

## High Priority - Code Quality

### Large Module Refactoring
**Goal**: Bring all modules under 200 lines per CLAUDE.md guidelines

**Critical Modules (>600 lines)**:
- [ ] database/schema.py - 651 lines → ~200 lines  
- [ ] ui/display_filter.py - 637 lines → ~200 lines

**High Priority (>500 lines)**:
- [ ] experiments/manager.py - 584 lines
- [ ] io/event_deserializer.py - 580 lines
- [ ] database/import_service.py - 563 lines
- [ ] cli/run.py - 454 lines (partially refactored from 862)
- [ ] core/router.py - 400+ lines
- [ ] providers/base.py - 400+ lines

**Medium Priority (>300 lines)**:
- [ ] core/conductor.py - 372 lines
- [ ] experiments/runner.py - 249 lines (partially refactored from 477)
- [ ] Plus ~8 more modules between 300-400 lines

Total: ~19 modules need refactoring to meet architectural guidelines

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

- ✅ Fixed post-processing chain (missing ManifestManager methods)
- ✅ Refactored monitor.py from 928 lines to 137 lines (split into 8 modules)
- ✅ Fixed token display in monitor
- ✅ Updated ARCHITECTURE.md to reflect current system
- ✅ Cleaned up outdated documentation files