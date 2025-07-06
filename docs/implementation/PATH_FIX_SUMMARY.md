# Path Fix Summary

## Problem
- Error: `FileNotFoundError: [Errno 2] No such file or directory: '/Users/ngl/work/pidgin/pidgin_output/experiments'`
- The system was looking in `/Users/ngl/work/pidgin` instead of the actual current directory

## Root Cause
- Different parts of the system were using different methods to determine the output directory
- Some used `PIDGIN_PROJECT_BASE`, others used `os.getcwd()`, etc.
- Inconsistent path resolution led to confusion

## Solution
Updated all path resolution to use the centralized `paths.py` module:

1. **EventStore** - Now uses `get_database_path()`
2. **ExperimentManager** - Now uses `get_experiments_dir()`
3. **ExperimentDaemon** - Now uses `get_database_path()`
4. **DaemonLauncher** - Sets both `PIDGIN_ORIGINAL_CWD` and `PIDGIN_PROJECT_BASE`
5. **OutputManager** - Now uses `get_output_dir()`

## Key Changes

### paths.py
- Single source of truth for all path resolution
- Priority order: `PIDGIN_ORIGINAL_CWD` → `PWD` → `os.getcwd()`
- Debug logging with `PIDGIN_DEBUG=1`

### Consistency
All components now use these functions:
- `get_output_dir()` - Base pidgin_output directory
- `get_experiments_dir()` - For experiments
- `get_conversations_dir()` - For conversations
- `get_database_path()` - For DuckDB file

## Testing
```bash
# Enable debug output to verify paths
PIDGIN_DEBUG=1 pidgin experiment list

# Should show correct path in your current directory
[DEBUG] Output directory: /Users/ngl/code/pidgin/pidgin_output
```

The system now consistently creates `pidgin_output/` in the user's current working directory, regardless of where pidgin is installed or how it's invoked.