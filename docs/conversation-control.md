# Conversation Control

## Current System
Pidgin currently uses a checkpoint-based pause/resume system. See implementation details in `docs/archive/conversation-control-checkpoints.md`.

## Upcoming Event-Based Control

With the event architecture, conversation control will be:

- **No checkpoints needed** - Event log IS the state
- **Natural pause/resume** - Stop processing events, continue later  
- **Perfect replay** - Replay events to any point
- **Parallel control** - Pause one experiment without affecting others

Control mechanisms:
- Subscribe to `ConversationPausedEvent`
- Emit `PauseRequestEvent` to pause
- Replay events from any point to resume

This will be implemented as part of the event architecture transition.