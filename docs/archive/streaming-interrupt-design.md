# Streaming Interrupt Solution for Pidgin

## Problem
Current interrupt mechanisms (Ctrl+Z, spacebar) don't work during blocking API calls. Users can only interrupt in brief moments between API responses, not during the long waits where they actually want to interrupt.

## Solution: Streaming with Interrupt Detection

Use provider streaming APIs to get natural interrupt points every ~100ms during response generation.

## Provider Support Status ✅
- **OpenAI**: Full streaming support
- **Anthropic**: Full streaming support  
- **Google Gemini**: `streamGenerateContent` available
- **xAI Grok**: Streaming confirmed in SDK examples

## Implementation Approach

### Core Flow
1. Replace `provider.get_response()` with `provider.stream_response()`
2. Process chunks with interrupt checking every ~100ms
3. On interrupt: show loading indicator, let API finish in background, display complete response
4. No token-by-token display needed - burn tokens for clean UX

### Code Pattern
```python
async def stream_response_with_interrupts(self, provider, messages):
    buffer = []
    last_check = time.time()
    
    # Show progress indicator
    self._show_thinking_indicator("Agent A is responding...")
    
    async for chunk in provider.stream_response(messages):
        buffer.append(chunk)
        
        # Check for interrupts every 100ms
        if time.time() - last_check > 0.1:
            if self._check_for_interrupt():
                # Immediate feedback
                self._update_indicator("Agent A is responding... [INTERRUPTED]")
                self._audio_bell()  # Confirm interrupt registered
                
                # Let API finish in background, burn the tokens
                remaining = [chunk async for chunk in provider.stream_response(messages)]
                buffer.extend(remaining)
                break
            last_check = time.time()
    
    # Display complete response in Rich panel (current behavior)
    full_response = ''.join(buffer)
    return Message(content=full_response)
```

## UX Design

### Normal Flow
- API call starts
- Response appears in Rich panel when complete (current behavior)

### Interrupted Flow  
- API call starts
- User hits spacebar/interrupt key
- Immediate audio feedback (bell)
- Visual indicator: "Agent A is responding... [INTERRUPTED]"
- Wait for API to complete (burn tokens)
- Display full response in Rich panel
- Enter conductor mode

## Key Benefits
- ✅ Actually works during API calls (main goal)
- ✅ No complex threading or architectural changes
- ✅ Clean Rich panel display (no flickering)
- ✅ Immediate user feedback
- ✅ Complete response context for conductor decisions
- ✅ Works across all providers uniformly

## Implementation Notes

### Provider Abstraction
```python
class Provider(Protocol):
    async def stream_response(self, messages: List[Message]) -> AsyncIterator[str]:
        """Stream response chunks for interrupt-friendly generation"""
```

### Token Considerations
- Interrupted responses still cost full token amount
- This is acceptable for good UX - token burn is minimal compared to engineering complexity
- Most interrupts happen early in responses anyway

### Audio Feedback
- System bell on interrupt confirmation
- Critical for immediate feedback while visual updates
- Cross-platform: `\a` or platform-specific bell

## Next Steps
1. Implement streaming in base Provider protocol
2. Add streaming support to each provider (AnthropicProvider, OpenAIProvider, etc.)
3. Replace blocking calls with streaming + interrupt detection
4. Test interrupt responsiveness across providers
5. Polish loading indicators and audio feedback

## Context from Architecture Discussion
This solution emerged from evaluating multiple interrupt approaches:
- File watching: Too wonky
- Signal handling: Platform issues
- Threading: Too complex
- Streaming: Natural interrupt points, clean implementation

The key insight: Accept token burn as the cost of good UX rather than fighting complex cancellation logic.