# Pidgin Directory Structure Refactoring Summary

## Date: 2025-08-08

## Objectives Completed ✅

### 1. XDG Base Directory Support
- Created `pidgin/io/directories.py` with XDG-compliant functions:
  - `get_config_dir()` → `~/.config/pidgin/` (respects `$XDG_CONFIG_HOME`)
  - `get_cache_dir()` → `~/.cache/pidgin/` (respects `$XDG_CACHE_HOME`)
  - `get_data_dir()` → `~/.local/share/pidgin/` (respects `$XDG_DATA_HOME`)

### 2. Configuration Directory Migration
- Updated all config references from `~/.pidgin/` to `~/.config/pidgin/`
- Modified files:
  - `pidgin/config/config.py` - Uses `get_config_dir()`
  - `pidgin/cli/info.py` - Uses `get_config_dir()`
  - Config file creation confirmed working at `~/.config/pidgin/pidgin.yaml`

### 3. Output Directory Changes
- Changed default from `pidgin_output/` to `pidgin/`
- Added smart detection for development environment:
  - Normal users: `./pidgin/`
  - Development (when run from source): `./pidgin_dev_output/`
- Updated `pidgin/constants/files.py` and `pidgin/io/paths.py`

### 4. Internal Structure Simplifications
- **Logs**: Now stored in experiment directories instead of centralized `logs/` folder
  - `experiment.log` and `startup.log` in each experiment directory
- **Filenames**: Simplified naming conventions
  - `events.jsonl` instead of `{conversation_id}_events.jsonl`
  - `transcript.md` instead of `{conversation_id}_transcript.md`
- **Active experiments**: Moved tracking to cache directory (`~/.cache/pidgin/active_experiments/`)
- **Database**: Located at `./pidgin/experiments.duckdb` (root of output directory)

### 5. Code Refactoring
- Updated experiment management modules:
  - `experiments/manager.py` - Uses cache for active experiments
  - `experiments/daemon_manager.py` - Logs go to experiment directories
  - `experiments/daemon_launcher.py` - Uses cache directory
  - `experiments/process_launcher.py` - Takes `base_dir` instead of `logs_dir`
  - `experiments/experiment_status.py` - Removed centralized logs references

### 6. Documentation Updates
- Updated CLI help text to show new paths
- Updated README.md with new output directory
- Updated .gitignore to handle both `pidgin_dev_output/` and legacy `pidgin_output/`

### 7. UI Improvements (Bonus)
- Enhanced CLI help display with Rich panels
- Added responsive layout based on terminal width
- Consistent Nord color theme throughout
- Better information hierarchy with Quick Start, Examples, Configuration sections

## Current Issues 🔴

### Primary Problem: Experiment Startup Hanging
When running `pidgin run -a local:test -b local:test -t 2`, the experiment:
1. Shows configuration successfully
2. Appears to start the daemon process
3. Hangs indefinitely without progressing
4. No PID files created in `~/.cache/pidgin/active_experiments/`
5. No experiment directories created in output location
6. No error messages or logs generated

### Potential Causes to Investigate:
1. **Path Resolution Issue**: The daemon launcher might be failing to resolve the correct output directory
2. **Permission Issue**: Cache or output directories might have permission problems
3. **Import Issue**: The pipx-installed version might be missing dependencies
4. **Async Event Loop**: Could be a deadlock in the event bus or daemon startup
5. **Process Launch**: The detached process launch might be failing silently

### Debugging Steps Needed:
1. Add debug logging to daemon launcher startup
2. Check if the subprocess is actually starting
3. Verify all paths are being resolved correctly
4. Test with synchronous execution instead of daemon mode
5. Check for any silent exceptions in the async code

## Files Modified (Key Changes)

### New Files:
- `pidgin/io/directories.py` - XDG directory management

### Modified Files:
- `pidgin/constants/files.py` - Changed `DEFAULT_OUTPUT_DIR`
- `pidgin/io/paths.py` - Added development detection logic
- `pidgin/config/config.py` - Use XDG config directory
- `pidgin/cli/__init__.py` - Enhanced help display, updated paths
- `pidgin/cli/info.py` - Use XDG config directory
- `pidgin/experiments/*.py` - Multiple files updated for new directory structure
- `pidgin/core/event_bus.py` - Simplified event file naming
- `.gitignore` - Updated for new output directories
- `README.md` - Updated output directory reference

## Testing Status

### Working ✅:
- Config file creation at `~/.config/pidgin/pidgin.yaml`
- XDG environment variable respect
- Help display enhancements
- Import and basic CLI functionality
- Package builds successfully with poetry
- Installs successfully with pipx

### Not Working ❌:
- Experiment execution hangs during startup
- No experiment output being generated
- Daemon process not creating PID files

## Next Steps

1. **Debug the hanging issue**:
   - Add verbose logging to daemon startup
   - Test without daemon mode (direct execution)
   - Check subprocess launching mechanism

2. **Verify path resolution**:
   - Ensure all components are using the same path resolution logic
   - Check that directories are being created with proper permissions

3. **Test in clean environment**:
   - Create a fresh virtual environment
   - Test outside the development directory
   - Verify all dependencies are properly included

## Commits Made

1. `refactor: complete module splitting to meet 200-line guideline`
2. `feat: enhance CLI help display with rich panels`
3. `fix: improve CLI help panel width consistency`
4. `refactor: implement XDG Base Directory support and simplify output structure`

## Summary

The refactoring successfully implemented XDG Base Directory compliance and simplified the internal directory structure. The configuration system now follows standard Linux/Unix conventions, and the output structure is cleaner and more logical. However, there's a critical issue with experiment execution that needs to be resolved before the refactoring can be considered complete.

The hanging issue appears to be related to the daemon process startup, possibly due to path resolution or process launching problems introduced during the refactoring. This needs immediate attention to restore full functionality.