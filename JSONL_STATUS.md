# JSONL Implementation Status

## Current State

The experiment list and status commands have been updated to use JSONL files exclusively for reading, completely bypassing the database to avoid lock issues.

### Changes Made:

1. **EventBus** (`pidgin/core/event_bus.py`):
   - Added JSONL writing functionality
   - Dual-write strategy: events go to both DuckDB and JSONL files
   - Each conversation gets its own JSONL file in `experiments/exp_id/events/`

2. **JSONLExperimentReader** (`pidgin/cli/jsonl_reader.py`):
   - New class that reads experiment data from JSONL files
   - Parses experiment and conversation status from event files
   - No database dependencies

3. **Experiment CLI** (`pidgin/cli/experiment.py`):
   - `list` command: Always uses JSONLExperimentReader, never touches database
   - `status` command: Always uses JSONLExperimentReader, never touches database
   - No more "Database locked, reading from event files..." messages
   - No more database retry attempts

### How It Works:

1. When experiments run, events are written to both:
   - DuckDB (for analytics, may be locked)
   - JSONL files (always readable, no locks)

2. When reading experiment data:
   - CLI commands use JSONLExperimentReader exclusively
   - No database connections are attempted
   - No retry loops or timeouts

### Testing:

To verify the implementation works correctly:

```bash
# List all experiments (reads from JSONL only)
pidgin experiment list

# List running experiments (reads from JSONL only)  
pidgin experiment list --all

# Check specific experiment (reads from JSONL only)
pidgin experiment status exp_abc123
```

If you're still seeing database lock errors, you may be running an older version of the code. Make sure you're using the latest version with these changes applied.