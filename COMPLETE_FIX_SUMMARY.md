# Complete Fix Summary

## Issues Fixed

### 1. Path Resolution Error
**Problem**: `FileNotFoundError: [Errno 2] No such file or directory: '/Users/ngl/work/pidgin/pidgin_output/experiments'`

**Root Causes**:
1. Inconsistent path resolution across different components
2. JSONLExperimentReader expecting directory structure that didn't exist
3. Looking for "events" subdirectory when JSONL files are directly in experiment directory

**Fixes Applied**:
1. **Centralized path resolution** - All components now use `paths.py`:
   - `EventStore` → uses `get_database_path()`
   - `ExperimentManager` → uses `get_experiments_dir()`
   - `OutputManager` → uses `get_output_dir()`
   - `DaemonLauncher` → sets both `PIDGIN_ORIGINAL_CWD` and `PIDGIN_PROJECT_BASE`

2. **JSONLExperimentReader fixes**:
   - Added check for non-existent directories (returns empty list)
   - Fixed to look for JSONL files directly in experiment directory (not in "events" subdirectory)
   - Updated glob pattern to `*_events.jsonl`

### 2. Auto-Attach Feature
**Implemented**: Experiments now automatically attach after starting

**Changes**:
- Default behavior: Start and immediately show progress
- Replaced `--daemon` with `--detach` flag
- Extracted attach logic into reusable `attach_to_experiment()` function
- Press Ctrl+C to detach (experiment continues in background)

## Usage

### Start experiment with auto-attach (default)
```bash
pidgin experiment start -a claude -b gpt -r 20 --name test
# Shows progress immediately
# Press Ctrl+C to detach
```

### Start detached (background only)
```bash
pidgin experiment start -a claude -b gpt -r 20 --name test --detach
```

### Re-attach later
```bash
pidgin experiment attach test
```

### Debug paths
```bash
PIDGIN_DEBUG=1 pidgin experiment list
```

## Directory Structure
```
./pidgin_output/               # In your current directory
├── experiments/
│   ├── experiments.duckdb
│   ├── exp_abc123/           # Experiment directory
│   │   ├── conv_exp_abc123_def456_events.jsonl
│   │   └── conv_exp_abc123_ghi789_events.jsonl
│   └── active/
│       └── exp_abc123.pid
└── conversations/
    └── 2024-01-01/
        └── 123456_abcde/
```

## Testing
The system has been rebuilt and all path issues should be resolved. The `pidgin_output` directory will be created in your current working directory, not in `/Users/ngl/work/pidgin`.