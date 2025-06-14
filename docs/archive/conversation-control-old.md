# Conversation Control

## Overview

Pidgin provides control mechanisms for managing AI conversations during research experiments. The system supports manual intervention and automated termination based on convergence metrics.

## Features

### 1. Manual Conversation Control

#### Pause Functionality
- Press `Ctrl+C` during any conversation to pause
- Current conversation state is saved to a checkpoint file
- Checkpoint includes all messages, turn count, and metadata
- Resume instructions are displayed after pausing

#### Resume Functionality
```bash
# Resume from specific checkpoint
pidgin resume path/to/conversation.checkpoint

# Resume from the latest checkpoint
pidgin resume --latest

# List available checkpoints
pidgin resume
```

### 2. Intervention Modes

#### Flowing Mode (Default)
- Conversation runs automatically
- Press `Ctrl+C` to pause and intervene
- Inject a message when paused
- Resume to continue the conversation
- Used for most research experiments

#### Manual Mode
- Enabled with `--manual` flag
- Pauses after EVERY turn
- Asks if you want to inject a message
- More control but tedious for long conversations

```bash
# Default flowing mode
pidgin chat -a claude -b gpt -t 100

# Manual mode for careful control
pidgin chat -a claude -b gpt -t 20 --manual
```

### 3. Convergence Detection

The primary validated metric for conversation dynamics:

#### What is Convergence?
- Measures how similar agents' communication styles become
- Score from 0.0 (completely different) to 1.0 (identical)
- Based on structural similarity: length ratios, sentence patterns, punctuation

#### Automatic Warnings
- Warning at 75% convergence (configurable)
- Auto-pause at 90% convergence
- Prevents conversations from becoming completely synchronized

#### Visual Indicators
```
Turn 45/100 | Conv: 0.82 ⚠️
```

### 4. Context Window Management

Prevents crashes from exceeding model context limits:

#### Automatic Tracking
- Each model's context limit is known (Claude: 200k, GPT: 128k)
- Tracks token usage throughout conversation
- Predictive warnings before hitting limits

#### Warning Thresholds
- 80% usage: Warning displayed
- 95% usage: Auto-pause to prevent crash

#### Turn Estimation
```
⚠️ Context Warning: 85.2% used, ~12 turns remaining
```

### 5. Experimental: Attractor Detection

**Note:** This is an experimental hypothesis, not a validated feature.

The system includes a framework for detecting structural patterns in conversations. This is being tested and validated through research.

## Configuration

### Basic Configuration

```yaml
# ~/.config/pidgin.yaml
conversation:
  convergence_threshold: 0.75  # Warning threshold
  
  # Experimental feature
  attractor_detection:
    enabled: false  # Disable until validated
    
context_management:
  warning_threshold: 80
  auto_pause_threshold: 95
```

### Command Line Overrides

```bash
# Disable experimental attractor detection
pidgin chat -a claude -b gpt --no-attractor-detection

# Custom convergence threshold
pidgin chat -a claude -b gpt --convergence-threshold 0.8
```

## Output Files

Conversations are saved to `~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/`:

- `conversation.json` - Full data with metrics:
  - Complete message history
  - Convergence scores per turn
  - Context usage statistics
  - Intervention records
  
- `conversation.md` - Human-readable transcript

- `conversation.checkpoint` - Resumable state (if paused)

## Usage Examples

### Basic Research Run
```bash
# Let it run until convergence or completion
pidgin chat -a claude -b claude -t 100
```

### Intervention When Needed
```bash
# Start conversation
pidgin chat -a opus -b gpt-4 -t 500

# When you see something interesting, press Ctrl+C
# > Change the topic to space exploration
# Resume continues from there
```

### Careful Debugging
```bash
# Manual mode for turn-by-turn control
pidgin chat -a claude -b gpt -t 20 --manual
```

## Key Indicators to Watch

1. **Convergence Score** - Are agents becoming too similar?
2. **Context Usage** - How close to the limit?
3. **Turn Count** - Progress through experiment

## Best Practices

1. **Let conversations flow** - Default mode is best for research
2. **Intervene sparingly** - Too many interventions affect natural dynamics
3. **Watch convergence** - High convergence might indicate interesting dynamics
4. **Save checkpoints** - Can always resume if something interesting happens
5. **Trust auto-pause** - Prevents crashes and captures interesting moments

## Keyboard Controls

- `Ctrl+C` - Pause conversation (only reliable option)
- `Enter` - Submit intervention message
- `Ctrl+D` - Alternative way to cancel input

Note: Spacebar interrupts and Ctrl+Z pause were explored but are not supported due to technical limitations with Rich.