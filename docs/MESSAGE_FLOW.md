# Message Flow and Memory Management

This document explains how messages flow through Pidgin, how they're transformed for different agents, and why the system doesn't need to keep all messages in memory.

## Overview

Messages in Pidgin go through several stages:
1. **Creation** - Agents generate messages in response to prompts
2. **Storage** - All messages are immediately written to JSONL files  
3. **Transformation** - Messages are reformatted for each agent's perspective
4. **Truncation** - Messages are trimmed to fit provider context windows
5. **Memory Management** - Only recent messages are kept in memory

## Message Transformation (Router)

The Router transforms the conversation history to match each agent's perspective. This is crucial for maintaining conversational coherence.

### How It Works

Each agent sees the conversation from their own perspective:
- Their own messages appear with role="assistant" 
- The other agent's messages appear with role="user"
- System prompts are adjusted to match the agent

### Example

Given this conversation history:
```
1. System: "You are Agent A"
2. Agent A: "Hello, I'm Alice"  
3. Agent B: "Hi Alice, I'm Bob"
4. Agent A: "Nice to meet you, Bob"
5. Agent B: "Likewise!"
```

**Agent A sees:**
```
1. System: "You are Agent A"
2. assistant: "Hello, I'm Alice"
3. user: "Hi Alice, I'm Bob"
4. assistant: "Nice to meet you, Bob"
5. user: "Likewise!"
```

**Agent B sees:**
```
1. System: "You are Agent B" (with A/B swapped in content)
2. user: "Hello, I'm Alice"
3. assistant: "Hi Alice, I'm Bob"
4. user: "Nice to meet you, Bob"
5. assistant: "Likewise!"
```

### Special Cases

- **Human interventions** are marked clearly: `[HUMAN]: message`
- **Choose-names mode** uses the same system prompt for both agents
- **Meditation mode** handles one agent facing silence

## Context Truncation (Providers)

After transformation, messages are truncated to fit within each provider's context window.

### Provider Limits

```python
CONTEXT_LIMITS = {
    "anthropic": 160000,    # 200k actual (80% safety margin)
    "openai": 100000,       # 128k actual  
    "google": 800000,       # 1M+ actual
    "xai": 100000,          # 128k actual
    "local": 4000,          # Most local models are 4k-8k
}
```

### Truncation Algorithm

The `ProviderContextManager` uses a binary search algorithm to find the optimal truncation point:

1. Always keep system messages
2. Calculate token estimate (1 token ≈ 3.5 chars)
3. Binary search to find how many recent messages fit
4. Return system messages + recent messages that fit

### Example

For a local model with 4k token limit:
- Full conversation: 50 messages, ~10k tokens
- After truncation: System prompt + last 15 messages, ~3.8k tokens
- Dropped: First 35 messages (still preserved in JSONL)

## Memory Management

### Current State

The `Conversation` object keeps all messages in memory:
```python
class Conversation(BaseModel):
    messages: List[Message] = []  # Grows unbounded
```

With default settings (20 turns = 40 messages), this is manageable. But for long conversations (100+ turns), memory usage can become significant.

### Why We Don't Need All Messages

Our investigation revealed that messages are only used for:

1. **Provider Context** - But providers truncate anyway via `apply_context_truncation()`
2. **Convergence Calculation** - Only needs last 10 messages (window_size)
3. **Rate Limiting** - Token estimation happens on truncated messages

### Future Optimization

Since all messages are stored in JSONL files, we can implement a sliding window:

```python
# Future implementation concept
class ConvergenceCalculator:
    def __init__(self, window_size=10, context_size=50):
        self.window_size = window_size      # For convergence
        self.context_size = context_size    # For providers
        self._messages = deque(maxlen=context_size)
    
    def add_message(self, message):
        self._messages.append(message)
    
    def get_recent_messages(self, n=None):
        return list(self._messages)[-n:] if n else list(self._messages)
```

## Token Tracking and Cost Calculation

Token tracking happens at multiple levels:

### Input Tokens
1. Messages are transformed by Router
2. Provider truncates to fit context window  
3. `estimate_messages_tokens()` calculates tokens on truncated messages
4. Used for rate limiting and cost estimation

### Output Tokens
1. Provider generates response
2. Actual token count from API (if available) or estimated
3. Emitted in `TokenUsageEvent` for tracking

### Key Insight
Token calculations are based on what's actually sent to the API (after transformation and truncation), not the full conversation history. This means memory optimization won't affect token tracking accuracy.

## Data Flow Diagram

```
┌─────────────┐
│   Message   │
│  Generated  │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│   EventBus  │────▶│ JSONL File   │ (Permanent storage)
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────────────┐
│ Conversation.messages│ (In-memory, currently unbounded)
└──────┬──────────────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌─────────────┐   ┌──────────────┐
│   Router    │   │ Convergence  │
│ Transform   │   │  Calculator  │
└──────┬──────┘   └──────────────┘
       │               (needs last 10)
       ▼
┌─────────────┐
│  Provider   │
│  Truncate   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     API     │
└─────────────┘
```

## Summary

1. **All messages are preserved** in JSONL files - nothing is lost
2. **Providers handle their own context windows** - automatic truncation
3. **Convergence only needs recent messages** - sliding window is sufficient
4. **Token tracking remains accurate** - based on truncated messages
5. **Memory can be optimized** without affecting functionality

The system is already well-designed to handle long conversations efficiently. The only optimization needed is to limit the in-memory message list to a sliding window, which can be elegantly tied to the ConvergenceCalculator.