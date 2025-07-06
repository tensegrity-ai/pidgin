# Screen-like Behavior Removal Summary

## What We Removed

### 1. `pidgin attach` Command
- Deleted `pidgin/cli/attach.py`
- Removed command registration from CLI
- Deleted `experiment_utils.py` (only contained attach functionality)
- Updated help text to remove attach references

### 2. Auto-attach Behavior
- Background experiments no longer auto-attach after starting
- Simplified to just show status command and tail instructions
- Removed --detach flag (replaced by simpler --quiet behavior)

## What We Kept

### `pidgin stop` Command
- Still valuable for graceful shutdown
- Handles database cleanup
- Can find experiments by ID (not just PID)
- Supports `--all` for batch operations

## What We Added

### Process Titles for Daemons
- Daemon processes now show as `pidgin-exp12345` in ps/top
- Uses optional `setproctitle` dependency
- Gracefully degrades if not installed
- Users can install with `pip install pidgin[daemon]` for better process names

## New Workflow

### Running Experiments
```bash
# Foreground (default) - see progress
pidgin run -a claude -b gpt

# Verbose - see messages
pidgin run -a claude -b gpt --verbose

# Background - fire and forget
pidgin run -a claude -b gpt --quiet
```

### Monitoring
```bash
# Check status
pidgin status
pidgin status exp_abc123

# Watch logs (standard Unix tools)
tail -f experiments/exp_abc123/*.jsonl
tail -f experiments/exp_abc123/conv_001.jsonl | jq .

# Check manifest
cat experiments/exp_abc123/manifest.json | jq .
```

### Stopping
```bash
# Stop specific experiment
pidgin stop exp_abc123

# Stop all experiments
pidgin stop --all

# Or use standard Unix (if you know the PID)
kill $(cat experiments/active/exp_abc123.pid)
```

## Benefits

1. **Simpler mental model** - No confusing attach/detach concepts
2. **More Unix-like** - Use standard tools for monitoring
3. **Less code** - Removed entire attach subsystem
4. **Better process visibility** - Daemons have meaningful names
5. **Cleaner CLI** - Fewer commands, clearer purpose

## Migration for Users

If you were using:
- `pidgin attach exp_123` → Use `tail -f experiments/exp_123/*.jsonl`
- `pidgin run ... --detach` → Use `pidgin run ... --quiet`
- Auto-attach behavior → Run in foreground (default) or use --quiet