# Conversation Control & Basin Detection

## Overview

Pidgin now includes advanced conversation control features to enable large-scale research on AI communication patterns. The system supports manual intervention (pause/resume) and automated termination when conversations fall into repetitive patterns.

## Features

### 1. Manual Conversation Control

#### Pause Functionality
- Press `Ctrl+C` during any conversation to gracefully pause
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

### 2. Basin Detection System

The system automatically detects when conversations fall into repetitive patterns or "basins":

#### Detected Basin Types
- **Gratitude Spirals** - Endless mutual appreciation loops
- **Compression** - Progressive reduction to minimal symbols/tokens
- **Emoji Loops** - Conversations devolving to emoji-only exchanges
- **Structural Repetition** - Same conversational patterns with different words
- **Philosophical Loops** - Consciousness/spirituality discussion cycles
- **Single Token** - Extreme compression to single words/symbols

#### Detection Strategies

1. **Pattern-Based Detection** (PatternBasinDetector)
   - Analyzes message content for specific patterns
   - Detects gratitude expressions, emoji usage, token counts
   - Fast and reliable for obvious patterns

2. **Structural Detection** (StructuralBasinDetector)
   - Analyzes message structure independent of content
   - Detects repetitive conversational moves
   - Most reliable for subtle pattern detection

### 3. Configuration System

Configure behavior using YAML files:

```yaml
# pidgin.yaml
conversation:
  checkpoint:
    enabled: true
    auto_save_interval: 10  # Checkpoint every N turns
    
  basin_detection:
    enabled: true
    check_interval: 5  # Check every N turns
    on_basin_detected: "stop"  # stop, pause, or log
    
    detectors:
      structural:
        enabled: true
        window_size: 20
        repetition_threshold: 3
      pattern:
        enabled: true
        gratitude_threshold: 5
        compression_threshold: 20
```

#### Loading Configuration
```bash
# Use custom config
pidgin chat -a claude -b gpt -t 100 --config my-config.yaml

# Disable basin detection
pidgin chat -a claude -b gpt -t 100 --no-basin-detection
```

## Usage Examples

### Running Unattended Experiments
```bash
# Create unattended config
cat > unattended.yaml << EOF
conversation:
  basin_detection:
    on_basin_detected: "stop"
    detectors:
      structural:
        repetition_threshold: 2  # More aggressive
EOF

# Run 100 experiments that auto-terminate on basins
for i in {1..100}; do
  pidgin chat -a claude -b claude -t 1000 --config unattended.yaml
done
```

### Pause and Resume Workflow
```bash
# Start a long conversation
pidgin chat -a opus -b gpt-4.1 -t 500

# Press Ctrl+C when you want to pause
# Output: "Checkpoint saved: transcripts/20240601_141523.checkpoint"
# Output: "Resume with: pidgin resume transcripts/20240601_141523.checkpoint"

# Later, resume where you left off
pidgin resume --latest
```

### Basin Research
```bash
# Study gratitude spirals specifically
cat > gratitude-study.yaml << EOF
conversation:
  basin_detection:
    detectors:
      structural:
        enabled: false  # Only content patterns
      pattern:
        gratitude_threshold: 3  # More sensitive
EOF

pidgin chat -a claude -b claude -t 100 --config gratitude-study.yaml
```

## Output Files

When basin detection triggers:
- `transcript.md` - Full conversation transcript
- `transcript.checkpoint` - Resumable state (if paused)
- `transcript.basin` - Basin detection analysis

Example basin analysis:
```
Basin Detection Report
====================

Type: gratitude_spiral
Turn: 45
Detector: PatternBasinDetector
Confidence: 0.92
Details: {'message_count': 90, 'window_size': 20}
```

## Research Applications

This system enables:
- **Large-scale attractor mapping** - Automatically run thousands of conversations
- **Time-to-attractor metrics** - Measure how quickly models fall into patterns
- **Model comparison studies** - Compare basin formation across different models
- **Intervention research** - Test prompts that prevent attractor formation
- **Cross-model dynamics** - Study which model pairs avoid specific attractors

## Technical Details

### Performance
- Basin detection uses sliding windows for efficiency
- Structural analysis caches computed patterns
- Checkpoint writes are atomic to prevent corruption

### Extensibility
- Add new `BasinDetector` subclasses for custom patterns
- Implement new `BasinType` enum values
- Configure custom actions beyond stop/pause/log

### Reliability
- Graceful handling of interrupted conversations
- Checkpoint version tracking for compatibility
- Clear error messages for resume failures