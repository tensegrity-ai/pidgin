# Large Module Refactoring Plan

## Overview
Multiple modules in the codebase exceed the 200-line guideline from CLAUDE.md. This plan outlines the refactoring needed to bring all modules into compliance.

## Modules Requiring Refactoring (Priority Order)

### Critical (>600 lines)
1. **monitor/monitor.py** - 845 lines (322% over limit)
2. **database/schema.py** - 651 lines (226% over limit)
3. **ui/display_filter.py** - 637 lines (219% over limit)

### High Priority (>500 lines)
4. **experiments/manager.py** - 584 lines (192% over limit)
5. **io/event_deserializer.py** - 580 lines (190% over limit)
6. **database/import_service.py** - 563 lines (182% over limit)
7. **analysis/notebook_cells.py** - 540 lines (170% over limit)
8. **database/transcript_formatter.py** - 522 lines (161% over limit)
9. **ui/tail_display.py** - 520 lines (160% over limit)
10. **experiments/state_builder.py** - 512 lines (156% over limit)

### Medium Priority (>300 lines)
11. **ui/display_utils.py** - 484 lines (142% over limit)
12. **database/event_store.py** - 477 lines (139% over limit)
13. **cli/run.py** - 454 lines (127% over limit) [Already refactored once]
14. **database/metrics_repository.py** - 434 lines (117% over limit)
15. **config/config.py** - 402 lines (101% over limit)
16. **cli/branch.py** - 391 lines (96% over limit)
17. **core/conductor.py** - 372 lines (86% over limit)
18. **metrics/flat_calculator.py** - 370 lines (85% over limit)
19. **core/rate_limiter.py** - 362 lines (81% over limit)
20. **analysis/convergence.py** - 355 lines (78% over limit)

## Refactoring Strategies

### 1. Monitor Module (845 → ~200 lines)
**Extraction Plan:**
- `monitor_display.py` - UI/panel building (~200 lines)
- `monitor_state.py` - State management (~180 lines)
- `error_tracker.py` - Error tracking (~150 lines)
- `metrics_calculator.py` - Metrics calculations (~100 lines)
- `monitor.py` - Main orchestration (~115 lines)

### 2. Database Schema (651 → ~200 lines)
**Extraction Plan:**
- `schema_definitions.py` - Table definitions (~200 lines)
- `schema_migrations.py` - Migration logic (~150 lines)
- `schema_indexes.py` - Index definitions (~100 lines)
- `schema_views.py` - View definitions (~100 lines)
- `schema.py` - Main orchestration (~101 lines)

### 3. Display Filter (637 → ~200 lines)
**Extraction Plan:**
- `filter_rules.py` - Filtering logic (~200 lines)
- `filter_formatters.py` - Message formatting (~200 lines)
- `filter_patterns.py` - Pattern matching (~137 lines)
- `display_filter.py` - Main filter (~100 lines)

### 4. Experiments Manager (584 → ~200 lines)
**Extraction Plan:**
- `experiment_lifecycle.py` - Start/stop logic (~200 lines)
- `experiment_state.py` - State management (~184 lines)
- `experiment_validation.py` - Validation logic (~100 lines)
- `manager.py` - Main orchestration (~100 lines)

### 5. Event Deserializer (580 → ~200 lines)
**Extraction Plan:**
- `event_parsers.py` - Event-specific parsers (~200 lines)
- `event_validators.py` - Validation logic (~180 lines)
- `event_factory.py` - Event creation (~100 lines)
- `event_deserializer.py` - Main logic (~100 lines)

## Common Patterns for Refactoring

1. **Separate Concerns**
   - UI/Display logic → separate display modules
   - Business logic → core modules
   - Data access → repository modules
   - Validation → validator modules

2. **Extract Helper Classes**
   - Complex methods → dedicated helper classes
   - Repeated patterns → utility modules
   - Configuration → separate config classes

3. **Use Composition**
   - Large classes → multiple smaller collaborating classes
   - Deep inheritance → composition with interfaces

4. **Follow Single Responsibility**
   - Each module should have ONE reason to change
   - Methods should do ONE thing well
   - Classes should have ONE primary responsibility

## Implementation Priority

### Phase 1: Critical Modules (Immediate)
- [ ] monitor/monitor.py
- [ ] database/schema.py
- [ ] ui/display_filter.py

### Phase 2: High Impact (Next Sprint)
- [ ] experiments/manager.py
- [ ] core/conductor.py
- [ ] database/event_store.py

### Phase 3: Medium Priority (Future)
- [ ] Remaining modules over 400 lines
- [ ] Modules between 300-400 lines
- [ ] Final cleanup of modules near 200 lines

## Success Metrics
- All modules under 200 lines
- Improved test coverage (easier to test smaller modules)
- Clearer separation of concerns
- Better code reusability
- Easier maintenance and debugging

## Notes
- Some modules already partially refactored (run.py, runner.py)
- Consider creating shared utility modules for common patterns
- Ensure backward compatibility during refactoring
- Write tests BEFORE extracting to ensure behavior preserved