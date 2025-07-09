# Console.print() Usage Audit

This document lists all locations where `console.print()` is being used directly instead of the display_utils functions.

## CLI Commands

### pidgin/cli/run.py
- Lines 165, 186, 195, 217, 353-375, 407, 426, 440, 459-478: Direct console.print() calls
- Mixed usage of display utilities and direct prints
- Configuration display section (lines 353-375) uses direct formatting
- Should use display.info(), display.warning(), display.error() etc.

### pidgin/cli/list_experiments.py
- Lines 96, 99: Direct console.print() for table display and tips
- Table display is appropriate, but tip could use display.dim()

### pidgin/cli/ollama_setup.py
- Line 113: Panel() usage for model setup display
- Lines 27-33: Direct console.print() for menu display
- Should use display utilities for consistency

### pidgin/cli/stop.py
- Line 86: Direct console.print() for spacing
- Mixed usage - some parts use display utilities, others don't

### pidgin/cli/init_config.py
- Lines 25-27, 39-45: Direct console.print() calls
- Should use display utilities for consistent styling

### pidgin/cli/info.py
- Lines 26, 40, 43, 79-85, 92-95, 113-117, 119-134, 139-198: Extensive direct console.print() usage
- Commands that show information/help text
- Should consider using display utilities for consistency

### pidgin/cli/models.py
- Lines 46, 53, 67, 89, 92-95: Direct console.print() calls
- Mixed with console.print_json() which is appropriate
- Information display could use display utilities

### pidgin/cli/monitor.py
- Lines 34-36, 41: Direct console.print() calls
- Should use display utilities

### pidgin/cli/__init__.py
- Lines 101-102, 119: Direct console.print() calls
- Banner display and "Coming soon" messages
- Could use display utilities

## Core Modules

### pidgin/core/conductor.py
- Lines 266, 302, 373, 380: Direct console.print() calls
- Debug and warning messages that should use display utilities
- Some are wrapped in dim() but not using display.dim()

### pidgin/config/config.py
- Lines 127-129: Direct console.print() calls during config creation prompt
- Should use display utilities for consistency

### pidgin/providers/ollama_helper.py
- Lines 67, 84-87, 91-92, 102, 108, 112, 129, 138, 152-155, 162, 166, 174-175: Extensive direct console.print() usage
- Installation and setup messages
- Should use display utilities throughout

### pidgin/core/conversation_lifecycle.py
- Line 266: Direct console.print() for warning
- Should use display.warning()

### pidgin/core/interrupt_handler.py
- Lines 44-46: Direct console.print() for interrupt notification
- Should use display utilities

## Summary

The codebase has inconsistent usage of display utilities. Many files use a mix of:
- Direct `console.print()` calls
- Direct `Panel()` usage
- Display utilities (display.info(), display.warning(), etc.)

### Priority Areas for Refactoring:
1. **CLI commands** - Especially run.py which has the most usage
2. **ollama_helper.py** - Has extensive direct usage during setup flows
3. **Info commands** - Large amounts of help text using direct prints

### Patterns to Address:
- Configuration display sections
- Menu/choice displays
- Progress/status messages
- Error and warning messages
- Information/help text display

All of these should be migrated to use the standardized display utilities for consistent styling and behavior across the application.