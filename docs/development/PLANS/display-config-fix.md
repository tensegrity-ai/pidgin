# Display Config Loading Fix

## Problem
Logger INFO messages "Loading config from: /Users/ngl/.config/pidgin/pidgin.yaml" appear in the middle of the display output, disrupting the clean formatting when showing the initial prompt in the chat display.

## Root Cause
In `pidgin/ui/tail/handlers.py` at line 70, a new `Config()` instance is created when displaying the initial prompt. This triggers `logger.info()` output that appears mid-display, breaking the visual flow.

## Solution: Pass Config Instance
Load Config once at display initialization and pass it to handlers that need it, avoiding multiple instantiations during display rendering.

## Implementation Steps

### 1. Modify TailDisplay to store Config
```python
# In pidgin/ui/tail/display.py
class TailDisplay:
    def __init__(self, ...):
        ...
        self.config = Config()  # Load once
        ...
```

### 2. Pass Config to Handlers
```python
# When creating handlers, pass the config
self.conversation_start_handler = ConversationStartHandler(
    self.console, 
    self.display_utils,
    self.config  # Pass config instance
)
```

### 3. Update ConversationStartHandler
```python
# In pidgin/ui/tail/handlers.py
class ConversationStartHandler:
    def __init__(self, console, display_utils, config):
        self.console = console
        self.display_utils = display_utils
        self.config = config  # Store passed config
    
    def handle(self, event):
        # Remove line 70: config = Config()
        # Use self.config instead
        human_tag = self.config.get("defaults.human_tag", "[HUMAN]")
        ...
```

### 4. Update Handler Creation
Ensure all handler instantiations in TailDisplay pass the config where needed.

## Benefits
- **Cleaner output**: No logger messages disrupting the display
- **Better architecture**: Single config instance per display session
- **Performance**: Config file read only once instead of multiple times
- **Testability**: Config can be easily mocked in tests
- **Consistency**: All handlers use the same config instance

## Testing
1. Run `pidgin run -a haiku -b haiku -t 5 -p "What is good in life?"`
2. Verify no "INFO Loading config from:" message appears in display
3. Verify initial prompt still shows correctly with proper human tag
4. Test with and without config file present

## Alternative Quick Fix (Not Recommended)
Change logger level from INFO to DEBUG in `config/config.py` lines 128 and 136. This hides the message but doesn't fix the architectural issue of multiple Config instantiations.