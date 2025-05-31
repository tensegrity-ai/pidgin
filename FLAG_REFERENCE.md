# Pidgin CLI Flag Reference

## Global Flags
- `-h, --help` - Show help for any command
- `-v, --verbose` - Enable verbose output
- `-V, --version` - Show version and exit
- `-c, --config` - Path to config file

## Create Commands

### `pidgin create experiment`
- `-n, --name` - Experiment name
- `-m, --model` - Models to use (can be used multiple times)
- `-t, --max-turns` - Maximum conversation turns
- `-c, --compression` - Enable compression testing
- `-s, --compression-start` - Turn to start compression
- `-M, --mediation` - Mediation level (full/light/observe/auto)
- `-i/-I, --interactive/--no-interactive` - Interactive mode

## Run Commands

### `pidgin run`
- `-r, --resume` - Resume paused experiment
- `-w/-W, --watch/--no-watch` - Watch live output

## Special Modes

### `pidgin meditate`
- `-m, --model` - Model to use
- `-s, --style` - Meditation style (wandering/focused/recursive/deep)
- `-t, --max-turns` - Maximum turns
- `-b, --basin-detection` - Stop when attractor state reached
- `-n, --name` - Experiment name
- `-r/-R, --run/--no-run` - Run immediately after creation

### `pidgin compress`
- `-m, --model` - Models to use (can be used multiple times)
- `-s, --start` - Turn to start compression
- `-r, --rate` - Compression rate increase per phase
- `-t, --max-turns` - Maximum turns
- `-n, --name` - Experiment name
- `-v/-V, --validation/--no-validation` - Include validation phases
- `-R/-N, --run/--no-run` - Run immediately after creation

## Management Commands

### `pidgin manage list`
- `-s, --status` - Filter by status
- `-l, --limit` - Number of experiments to show
- `-a, --all` - Show all experiments

### `pidgin manage show`
- `-t, --transcript` - Show full transcript
- `-m, --metrics` - Show detailed metrics

### `pidgin manage remove`
- `-f, --force` - Skip confirmation

## Analysis Commands

### `pidgin analyze`
- `-c/-C, --compression/--no-compression` - Analyze compression
- `-s/-S, --symbols/--no-symbols` - Analyze symbol emergence
- `-e, --export` - Export analysis to file

## Model Commands

### `pidgin models list`
- `-v, --verbose` - Show all model IDs

## Quick Reference

Most common operations:
```bash
# Quick experiment creation
pidgin create -n "Test" -m claude -m gpt

# Run with live view
pidgin run <id> -w

# Quick meditation
pidgin meditate -m claude -s deep

# List recent experiments
pidgin manage list -l 10

# Analyze with export
pidgin analyze <id> -e results.json
```

## Design Principles

1. **Single letters are meaningful**: 
   - `-n` for name
   - `-m` for model
   - `-t` for time/turns
   - `-s` for start/status/style (context-dependent)
   - `-r` for resume/run/rate (context-dependent)

2. **Boolean flags use uppercase for negation**: 
   - `-i/-I` for interactive/no-interactive
   - `-w/-W` for watch/no-watch

3. **Help is always available**: 
   - Every command supports `-h` or `--help`
   - Commands with required arguments show help when called without args