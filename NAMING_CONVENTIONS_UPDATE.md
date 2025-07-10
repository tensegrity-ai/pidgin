# Experiment Naming and Output Organization Update

## Overview

Implemented enhanced experiment naming and output organization to make it easier to identify and work with experiments.

## Key Changes

### 1. Enhanced Directory Naming

Experiment directories now follow the format: `exp_id_name_date`

Example: `exp_0834a7b2_curious-echo_2025-01-10`

This includes:
- The experiment ID (for uniqueness)
- The experiment name (for human readability)
- The date (for temporal context)

### 2. Automatic README Generation

Each experiment directory now gets an auto-generated `README.md` that includes:
- Experiment name and ID
- Start/end times and duration
- Configuration details (agents, parameters)
- Results summary (conversations completed, total turns)
- Conversation breakdown with status
- Quick analysis commands

### 3. Improved Experiment Resolution

The `resolve_experiment_id` method now supports:
- Full experiment ID: `exp_a1b2c3d4`
- Shortened ID: `a1b2c3d4`
- Experiment name: `curious-echo`
- Directory name: `exp_a1b2c3d4_curious-echo_2025-01-10`
- Partial ID matching: `a1b2`

## Implementation Details

### Files Modified

1. **`pidgin/experiments/manager.py`**:
   - Updated `start_experiment` to create directories with enhanced naming
   - Updated `resolve_experiment_id` to handle new directory format
   - Updated `_find_experiment_by_name` to check directory names
   - Updated `list_experiments`, `get_logs`, and `tail_logs` to use resolution

2. **`pidgin/experiments/readme_generator.py`** (new):
   - Created `ExperimentReadmeGenerator` class
   - Generates comprehensive README from manifest data
   - Includes formatting helpers for timestamps and status

3. **`pidgin/experiments/runner.py`**:
   - Updated `_import_and_generate_transcripts` to generate README
   - README generation happens before database import

### Directory Structure Example

```
experiments/
├── exp_0834a7b2_curious-echo_2025-01-10/
│   ├── README.md           # Auto-generated summary
│   ├── manifest.json       # Experiment metadata
│   ├── conv_001.jsonl      # Conversation events
│   ├── conv_002.jsonl      # Conversation events
│   └── transcripts/        # Human-readable output
└── active/
    └── exp_0834a7b2.pid    # Daemon process ID
```

### Backward Compatibility

The implementation maintains backward compatibility:
- Old experiment directories (just `exp_id`) still work
- Resolution handles both old and new formats
- No changes to database schema or JSONL format

## Benefits

1. **Easier Identification**: Can identify experiments by name in file browser
2. **Better Organization**: Date in directory name helps with chronological sorting
3. **Quick Overview**: README provides at-a-glance experiment details
4. **Flexible Access**: Can reference experiments by name, ID, or directory

## Next Steps (Optional)

1. Add timestamps to JSONL filenames (e.g., `conv_001_2025-01-10_143022.jsonl`)
2. Update CLI list command to show directory names
3. Add experiment search/filter capabilities
4. Consider adding tags or categories to experiments