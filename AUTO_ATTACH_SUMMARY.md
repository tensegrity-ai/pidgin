# Auto-Attach and Path Improvements

## Changes Made

### 1. Fixed pidgin_output Directory Creation
- Improved `get_output_dir()` in `paths.py` to be more robust
- Added debug logging (enabled with `PIDGIN_DEBUG=1`)
- Ensures `pidgin_output/` is created in user's current working directory
- Priority order: PIDGIN_ORIGINAL_CWD → PWD → os.getcwd()

### 2. Auto-Attach Feature for Experiments
- **Default behavior changed**: Experiments now automatically attach after starting
- Shows live progress bar immediately after starting an experiment
- Use Ctrl+C to detach (experiment continues running in background)
- Can re-attach anytime with `pidgin experiment attach <name>`

### 3. New --detach Flag
- Replaced `--daemon` with `--detach` flag
- Use `--detach` to start experiment in background without attaching
- More intuitive naming that matches the attach/detach paradigm

### 4. Code Improvements
- Extracted attach logic into reusable `attach_to_experiment()` function
- Updated OutputManager to use consistent path logic
- Better error handling and user feedback

## Usage Examples

### Default: Start and Watch
```bash
# Starts experiment and immediately shows progress
pidgin experiment start -a claude -b gpt -r 20 --name mytest

# Press Ctrl+C to detach and let it run in background
```

### Background Only
```bash
# Start detached (old --daemon behavior)
pidgin experiment start -a claude -b gpt -r 20 --name mytest --detach
```

### Re-attach Later
```bash
# Attach to see progress
pidgin experiment attach mytest

# Or with event stream
pidgin experiment attach mytest --tail
```

## Benefits

1. **More intuitive UX**: Users see progress immediately by default
2. **Consistent paths**: pidgin_output always in user's CWD
3. **Flexible monitoring**: Easy to attach/detach as needed
4. **Clean code**: Reusable attach logic, better organization

## Testing

Enable debug output to verify paths:
```bash
PIDGIN_DEBUG=1 pidgin chat -a local:test -b local:test -t 1
```

The system will show where pidgin_output is being created.