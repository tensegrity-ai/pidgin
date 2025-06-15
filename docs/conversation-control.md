# Conversation Control

## Current Implementation ✅

### Interrupt System

Press `Ctrl+C` during any conversation to pause:

1. **Signal Handling**: Ctrl+C is caught by custom handler
2. **Graceful Completion**: Current message finishes
3. **Pause Menu**: Two options: Continue or Exit
4. **Event Logging**: All transitions recorded

This is fully working and tested.

### How It Works

```python
# In conductor.py:
1. Signal handler set up at conversation start
2. Ctrl+C sets interrupt_requested flag
3. Check between turns for interrupt
4. If interrupted, show pause menu
5. Continue or exit based on choice
```

All pause/resume actions emit events:
- `InterruptRequestEvent` - User pressed Ctrl+C
- `ConversationPausedEvent` - Conversation paused
- `ConversationResumedEvent` - User chose to continue

## Not Yet Implemented ❌

### Message Injection
- Framework exists but not connected
- Would allow adding messages during pause
- Planned for future release

### Convergence-Based Pausing
- Code calculates convergence metrics
- Auto-pause at threshold NOT implemented
- Needs UI integration

### Context Limit Pausing  
- Token counting exists but not active
- No automatic pausing at context limits
- Manual implementation needed

### Event Replay Resume
- Cannot resume from previous conversations
- Event logs exist but replay not implemented
- Checkpoint system was removed