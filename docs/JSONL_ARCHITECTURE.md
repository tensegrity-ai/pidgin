# JSONL-First Event Architecture

## Overview

Pidgin uses a JSONL-first approach for event storage to avoid DuckDB concurrency issues. Events are written to append-only JSONL files during execution, then batch-loaded to DuckDB after completion for analytics.

## Architecture

```
During Execution:
Events → JSONL files (append-only, no locking)

After Completion:
JSONL files → Batch Load → DuckDB (analytics)
```

## Benefits

1. **Zero Concurrency Issues**: Append-only files have no locking
2. **Crash Resilient**: State rebuilds from events  
3. **Debuggable**: Use standard Unix tools (grep, jq, tail)
4. **Fast**: File reads with OS caching
5. **Simple**: No complex coordination needed

## Implementation Details

### Event Storage

- Events written to `{conversation_id}_events.jsonl`
- One line per event, standard JSON format
- Files organized by experiment: `experiments/{exp_id}/`
- Single chats go to timestamped directories

### State Reconstruction

The `StateBuilder` class rebuilds state from JSONL:

```python
state = StateBuilder.from_experiment_dir(exp_dir)
# Returns lightweight ExperimentState with:
# - progress, status, active conversations
# - convergence scores, timing info
```

### Monitoring Commands

All monitoring commands read from JSONL, not database:

- `pidgin experiment list` - List experiments
- `pidgin experiment attach <id>` - Live progress 
- `pidgin monitor` - System-wide view
- `pidgin experiment status` - Check specific experiment

### Automatic Batch Loading

**Experiments**: Loaded to DuckDB automatically after completion
- Happens in `ExperimentRunner._batch_load_to_database()`
- Creates `.loaded_to_db` marker file
- Failures don't affect experiment success

**Single Chats**: Loaded to DuckDB automatically after completion  
- Happens in `Conductor._batch_load_chat_to_database()`
- Goes to `~/.pidgin/chats.duckdb`
- Best-effort, failures are silent

**Manual Loading**: Use `pidgin load-db` command (hidden)
- Load specific experiments: `pidgin load-db exp_abc123`
- Load all completed: `pidgin load-db --all`
- Force reload: `pidgin load-db exp_abc123 --force`
- Note: This is a hidden command for advanced users/debugging

## File Formats

### JSONL Event Format

```json
{"timestamp": "2024-01-01T12:00:00", "event_type": "TurnCompleteEvent", "conversation_id": "conv_123", "turn_number": 5, "convergence_score": 0.75}
{"timestamp": "2024-01-01T12:00:01", "event_type": "MessageCompleteEvent", "conversation_id": "conv_123", "agent_id": "agent_a", "content": "Hello!"}
```

### Directory Structure

```
pidgin_output/
├── experiments/
│   ├── experiments.duckdb      # Analytics database
│   ├── exp_abc123/            # Experiment directory
│   │   ├── conv_exp_abc123_def456_events.jsonl
│   │   ├── conv_exp_abc123_ghi789_events.jsonl
│   │   └── .loaded_to_db      # Marker file
│   └── exp_xyz789/
└── chats/
    └── 20240101_120000_abc123/
        ├── conv_abc123_events.jsonl
        └── .loaded_to_db
```

## Development Notes

1. **Never read from database during active operations**
2. **JSONL is source of truth during execution**
3. **DuckDB is for post-hoc analytics only**
4. **All display/monitoring uses StateBuilder**
5. **Batch loading is automatic but can fail silently**

## Future Enhancements

- Event replay for conversation resume
- Compressed JSONL archives for old experiments
- Streaming analytics from JSONL
- GraphQL server reading from both JSONL and DuckDB