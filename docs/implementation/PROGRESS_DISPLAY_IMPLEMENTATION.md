# Progress Display Implementation

## Overview

We've implemented a centered progress panel as the new default display mode for `pidgin run`. This provides researchers with key metrics at a glance without overwhelming them with details.

## Changes Made

### 1. New Display Modes
- **Default (progress)**: Centered panel with turn progress, convergence, and token costs
- **--verbose**: Shows conversation messages with minimal metadata
- **--tail**: Shows raw event stream (like tail -f)
- **--quiet**: Runs in background with notification when complete

### 2. New Files Created

#### `pidgin/display/progress_panel.py`
- `ProgressPanel` class that creates the centered display
- Tracks conversation and experiment progress
- Shows convergence scores with trend indicators (↑, ↑↑, →, ↓, ↓↓)
- Displays token usage and cost in real-time
- Supports both single and multiple conversation modes

#### `pidgin/ui/progress_display.py`
- `ProgressDisplay` class that integrates with the event system
- Subscribes to conversation events
- Updates the progress panel based on events
- Calculates costs using model-specific pricing
- Manages Rich.Live display lifecycle

### 3. Modified Files

#### `pidgin/cli/run.py`
- Changed default display mode to "progress"
- Updated --quiet to automatically enable background mode and notifications
- Updated --verbose description to clarify it shows live messages
- Improved command documentation

#### `pidgin/core/conversation_lifecycle.py`
- Added support for "progress" display mode
- Creates and manages ProgressDisplay when mode is "progress"
- Ensures proper cleanup of live display on conversation end

## Display Examples

### Single Conversation
```
╭─────────────────────────────────────────────────────────────╮
│             Claude ↔ GPT-4: philosophy_test                 │
│                                                             │
│  Turn  12/50  ████████░░░░░░░░░░░░ 24%  Conv: 0.34 ↑      │
│                                                             │
│              2.3k tokens ($0.08)                            │
╰─────────────────────────────────────────────────────────────╯
```

### Multiple Conversations
```
╭─────────────────────────────────────────────────────────────╮
│            Claude ↔ GPT-4: philosophy_batch                 │
│                                                             │
│  Conv   3/10  ███░░░░░░░░░░░░░░░░░ 30%                    │
│  Turn  18/50  ███████░░░░░░░░░░░░░ 36%  Conv: 0.41 ↑↑     │
│                                                             │
│         18.5k tokens ($0.72) • ~620 tok/conv               │
│                                                             │
│          [2 complete: avg 0.38] [0 failed]                 │
╰─────────────────────────────────────────────────────────────╯
```

## Benefits

1. **Clear Progress Tracking**: Researchers can see exactly where they are in the experiment
2. **Cost Awareness**: Real-time token usage and cost calculation helps manage API budgets
3. **Convergence Monitoring**: Visual indicators show when conversations are converging
4. **Non-intrusive**: Clean, centered display that updates smoothly
5. **Flexible**: Easy to switch to verbose mode to see actual messages

## Testing

Run `python3 test_progress_display.py` to see the progress panel in action with simulated data.

## Future Enhancements

1. Add configurable cost alerts (e.g., flash when approaching budget limits)
2. Support for custom color themes
3. Export progress snapshots
4. Add ETA based on token rate (if reliable)