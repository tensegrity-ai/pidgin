# Extensible Router Architecture

## Design Principle
Ship 2-agent conversations today, but architect for N-agents tomorrow without overengineering.

## Current Minimal Change

```python
# Instead of DirectRouter with hardcoded agent_a/agent_b logic:

class Router:
    """Base router that could support N agents"""
    def __init__(self, agents: List[Agent], providers: Dict[str, Provider]):
        self.agents = agents
        self.providers = providers
        self.message_history: List[Message] = []
    
    async def get_next_message(self) -> Message:
        """Get next message in conversation"""
        raise NotImplementedError

class TwoAgentRouter(Router):
    """Current implementation - simple alternation"""
    def __init__(self, agents: List[Agent], providers: Dict[str, Provider]):
        assert len(agents) == 2, "TwoAgentRouter requires exactly 2 agents"
        super().__init__(agents, providers)
        self.last_speaker_idx = 1  # Start with agent 0
    
    async def get_next_message(self) -> Message:
        # Current logic, but using indices instead of hardcoded names
        self.last_speaker_idx = (self.last_speaker_idx + 1) % 2
        current_agent = self.agents[self.last_speaker_idx]
        
        # Build message history from perspective of current agent
        # (existing logic here)
        
        response = await self.providers[current_agent.id].get_response(messages)
        return Message(
            role="assistant",
            content=response,
            agent_id=current_agent.id
        )
```

## Key Abstractions That Enable Future Extension

### 1. Message Attribution
```python
@dataclass
class Message:
    role: str
    content: str
    agent_id: str
    
    # Future-ready fields (optional)
    to_agents: Optional[List[str]] = None  # Who is this addressed to?
    metadata: Optional[Dict] = None        # For experiments, timing, etc.
```

### 2. Conversation State
```python
class ConversationState:
    agents: List[Agent]
    messages: List[Message]
    
    def get_messages_for_agent(self, agent_id: str) -> List[Message]:
        """Build message history from an agent's perspective"""
        # This abstraction lets us later handle complex multi-party views
```

### 3. Router Interface
```python
class Router(Protocol):
    """Any router must implement this simple interface"""
    
    async def get_next_message(self) -> Optional[Message]:
        """Get the next message in the conversation"""
        ...
    
    def should_continue(self) -> bool:
        """Determine if conversation should continue"""
        ...
```

## Benefits of This Approach

### Shipping Today
- Minimal changes to current code
- Just refactor DirectRouter → TwoAgentRouter
- Everything else stays the same
- No new complexity for users

### Enabling Tomorrow
When we want 3+ agents, we can:
1. Add `ThreeAgentRouter` without touching existing code
2. Experiment with different strategies
3. Let CLI detect agent count and choose router:
   ```python
   if len(agents) == 2:
       router = TwoAgentRouter(agents, providers)
   elif len(agents) == 3:
       router = ThreeAgentRoundRobinRouter(agents, providers)
   else:
       raise ValueError(f"Unsupported agent count: {len(agents)}")
   ```

### Research Benefits
- Clean separation between routing strategy and core engine
- Easy to A/B test different multi-agent strategies
- Can add experimental routers without breaking stable code
- Message format already supports attribution

## What We DON'T Do Now
- No complex graph structures
- No cocktail party modes
- No interaction topologies
- No coalition detection
- Just clean abstractions

## Future Router Examples (Not Built Yet)
```python
class ThreeAgentDebateRouter(Router):
    """A moderates debate between B and C"""
    
class RoundRobinRouter(Router):
    """Simple rotation through N agents"""
    
class ResponseToAllRouter(Router):
    """Each agent responds to previous speaker"""
```

## The Key Insight

By making three simple changes:
1. `List[Agent]` instead of hardcoded agent_a/agent_b
2. Router as pluggable strategy
3. Messages that know their sender

We preserve simplicity while leaving the door open for controlled experimentation with multi-agent dynamics later.

## Implementation Priority

1. **Now**: Refactor to this structure, ship 2-agent
2. **Later**: Add 3-agent round-robin as experimental feature
3. **Much Later**: Explore complex topologies if research demands it

This way we're not overengineering, but we're also not painting ourselves into a corner.