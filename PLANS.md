# Development Plans

This document tracks development tasks with optimal sequencing for maximum effectiveness.

## IMMEDIATE PRIORITY - Critical Code Quality Issues

### Phase 1: Monster Function Refactoring (✅ COMPLETED 2025-08-10)
- [x] **branch.py refactoring** - Reduced from 295 lines to ~105 lines
  - Extracted into 5 focused components:
    - BranchSourceFinder (44 lines)
    - BranchConfigBuilder (128 lines)
    - BranchSpecWriter (51 lines)
    - BranchExecutor (135 lines)
    - BranchSource model (27 lines)
  - All components well under 200-line guideline

### Phase 2: Parameter Explosion Fix (4 hours)
- [ ] **run.py refactoring** - 23 parameters in run() function
  - Apply same pattern as branch.py (builder/validator/executor)
  - Create RunConfigBuilder for parameter management
  - Extract validation logic into RunValidator

## HIGH PRIORITY - Architecture Improvements

### Week 1: Core CLI Infrastructure
- [ ] **Create CLIErrorHandler** - Standardize error handling across all CLI commands
- [ ] **Apply component pattern to run.py** - Using learnings from branch.py
- [ ] **Extract CLIDisplay mixin** - Common display patterns across CLI modules

### Week 2: Type Safety & Exception Handling
- [ ] **Add type hints to CLI modules** - Start with entry points
- [ ] **Replace generic exceptions** (68 instances) - Use specific exception types
- [ ] **Configure mypy** - Set up type checking in CI pipeline
- [ ] **Add error context** - Meaningful error messages throughout

### Week 3: Testing Infrastructure
- [ ] **Integration tests** - For refactored branch.py and run.py
- [ ] **Unit tests** - For new component classes
- [ ] **Performance benchmarks** - Establish baselines
- [ ] **Test coverage targets** - Aim for 80%+ on critical paths

### Week 4: Module Size Evaluation
- [ ] **Analyze large modules** - Determine which need splitting vs. which are justified
  - ui/display_utils.py - 484 lines
  - database/event_store.py - 483 lines (may be acceptable as central component)
  - database/repositories/metrics_repository.py - 434 lines
  - config/config.py - 386 lines
  - core/conductor.py - 378 lines
- [ ] **Extract calculation logic** - Move from repositories to dedicated modules
- [ ] **Document architectural decisions** - Why certain modules remain large

## MEDIUM PRIORITY - Documentation & Standards

### Documentation Updates
- [ ] Update examples to reflect new component patterns
- [ ] Add troubleshooting guide for common issues
- [ ] Document context limit behavior
- [ ] Create architecture decision records (ADRs)

### Code Standards
- [ ] Establish naming conventions for component classes
- [ ] Document testing requirements
- [ ] Create PR template with quality checklist

## LOW PRIORITY - Future Enhancements

### Nice-to-Have Features
- [ ] Progress bars for long experiments
- [ ] Experiment resume capability
- [ ] Custom analysis plugins
- [ ] Additional export formats (CSV, Parquet)
- [ ] Desktop notifications for experiment completion

## Completed Tasks

### 2025-08-10: Branch.py Refactoring
- ✅ Successfully refactored 295-line monster function to ~105 lines
- ✅ Created 5 focused, single-responsibility components
- ✅ All new modules under 200 lines (largest is 135 lines)
- ✅ Clean separation of concerns: finding, configuring, writing, executing
- ✅ Improved testability and maintainability

### 2025-08-10: Subprocess/Daemon Fixes
- ✅ Fixed console initialization in subprocess (TailDisplay handles None console)
- ✅ Fixed import error (get_database_path was in wrong module)
- ✅ Fixed missing directory creation in ExperimentManager
- ✅ Cleaned up unused log file path in daemon.py
- ✅ Added comprehensive test suite for daemon/subprocess functionality
- ✅ All 26 tests passing

### 2025-08-10: Code Quality Analysis
- ✅ Performed comprehensive code smell analysis
- ✅ Identified 28 issues (2 critical, 8 high, 12 medium, 6 low)
- ✅ Created detailed refactoring strategy

## Implementation Notes

### Key Principles
- **No backwards compatibility required** - Make clean, optimal design decisions
- **Focus on research integrity** over engineering convenience
- **Some modules may exceed 200 lines** if they're central architectural components
- **Prioritize worst violations first** - Start with the most egregious issues
- **Keep changes minimal and well-documented** - Small, focused PRs

### Success Metrics
- All functions under 50 lines (with rare, justified exceptions)
- No function with more than 6 parameters
- All modules under 300 lines (200 ideal, 300 acceptable, 500 hard limit)
- Zero generic exception handlers in new code
- 80%+ test coverage on refactored code

### Timeline
- **Week 1-2**: Critical refactorings (branch.py, run.py, error handling)
- **Week 3-4**: Type safety and testing infrastructure
- **Month 2**: Module reorganization and documentation
- **Ongoing**: Incremental improvements as we touch code

## References
- `PLANS/branch-refactoring.md` - Detailed branch.py refactoring plan
- `CLAUDE.md` - Development guidelines and philosophy
- `CODE_QUALITY_PLAN.md` - Comprehensive code smell analysis