# Streaming Interrupt Implementation

## Overview
This implementation adds streaming response capability with spacebar interrupt functionality to Pidgin. Users can now interrupt AI responses mid-stream by pressing the spacebar, gaining immediate control through the conductor system.

## Key Changes

### 1. Provider Updates
All providers now implement `stream_response()` method instead of `get_response()`:
- **AnthropicProvider**: Uses `client.messages.stream()` 
- **OpenAIProvider**: Uses `stream=True` parameter
- **GoogleProvider**: Uses `send_message(..., stream=True)`
- **xAIProvider**: Uses OpenAI-compatible streaming

### 2. Router Enhancement
- Added `get_next_response_stream()` method that yields (chunk, agent_id) tuples
- Backward compatibility maintained - `get_next_response()` now uses streaming internally

### 3. Dialogue Engine Updates
- New `_get_agent_response_streaming()` method handles streaming with interrupt detection
- Checks for spacebar every 100ms during streaming
- Shows character count progress
- Plays system bell on interrupt
- Displays partial response immediately when interrupted

### 4. Terminal Utilities
- Created `/pidgin/utils/terminal.py` with cross-platform keyboard detection
- `raw_terminal_mode()` context manager for Unix/Linux/macOS
- `check_for_spacebar()` works on all platforms

### 5. UI Updates
- Changed all "Press Ctrl+Z to pause" to "Press Spacebar to interrupt"
- Updated control displays throughout the application

## User Experience

### Normal Flow
1. API call starts
2. Status line shows: "Streaming... X chars | Press SPACE to interrupt"
3. Response appears in Rich panel when complete

### Interrupted Flow
1. API call starts streaming
2. User presses spacebar
3. System bell sounds (audio feedback)
4. Partial response displayed immediately
5. Conductor enters paused mode for intervention
6. User can inject messages or continue

## Testing

Run the test script to verify streaming works:
```bash
python test_streaming.py
```

To test in a real conversation:
```bash
pidgin chat "Hello, tell me a long story"
```

Then press spacebar during the response to interrupt.

## Implementation Notes

- Streaming is now the default for all providers
- Token costs remain the same (we don't cancel the API request)
- Partial responses are saved to conversation history
- Cross-platform compatible (Windows, macOS, Linux)
- Minimal performance overhead from interrupt checking

## Future Enhancements

- Visual progress indicator (spinner/progress bar)
- Configurable interrupt key
- Option to cancel API request (provider-dependent)
- Streaming response preview in status line