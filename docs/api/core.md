# Core APIs

The core module provides the fundamental APIs for running and managing conversations.

## Conductor

The `Conductor` class orchestrates conversations between agents.

```python
from pidgin.core import Conductor
from pidgin.io.output_manager import OutputManager

conductor = Conductor(
    output_manager=output_manager,
    bus=event_bus,  # Optional event bus
    convergence_threshold_override=0.95  # Optional convergence threshold
)
```

### Methods

#### `run_conversation()`

Run a complete conversation between two agents.

```python
async def run_conversation(
    agent_a: Agent,
    agent_b: Agent,
    initial_prompt: str,
    max_turns: int = 10,
    display_mode: str = "normal",
    show_timing: bool = False,
    choose_names: bool = False,
    awareness_a: str = "basic",
    awareness_b: str = "basic",
    temperature_a: Optional[float] = None,
    temperature_b: Optional[float] = None,
    conversation_id: Optional[str] = None,
    prompt_tag: Optional[str] = None,
    branch_messages: Optional[list] = None,
) -> Conversation
```

**Parameters:**
- `agent_a`, `agent_b`: The participating agents
- `initial_prompt`: Starting prompt for the conversation
- `max_turns`: Maximum number of message exchanges
- `display_mode`: Output display ("normal", "quiet", "chat")
- `show_timing`: Whether to display timing information
- `choose_names`: Allow agents to choose their own names
- `awareness_a`, `awareness_b`: System prompt awareness levels
- `temperature_a`, `temperature_b`: Optional temperature overrides
- `conversation_id`: Pre-assigned conversation ID (auto-generated if None)
- `prompt_tag`: Load prompt from CLAUDE.md by tag
- `branch_messages`: Previous messages for branching

**Returns:** Complete `Conversation` object

**Example:**
```python
conversation = await conductor.run_conversation(
    agent_a=Agent(id="agent_a", model="claude"),
    agent_b=Agent(id="agent_b", model="gpt-4"),
    initial_prompt="Discuss the implications of AGI",
    max_turns=20,
    temperature_a=0.7,
    temperature_b=0.9
)
```

## Event Bus

The event bus enables loose coupling between components.

```python
from pidgin.core.event_bus import EventBus
from pidgin.core.events import TurnCompleteEvent

bus = EventBus()

# Subscribe to events
async def handle_turn(event: TurnCompleteEvent):
    print(f"Turn {event.turn_number} convergence: {event.convergence_score}")

bus.subscribe(TurnCompleteEvent, handle_turn)

# Emit events
await bus.emit(TurnCompleteEvent(
    conversation_id="conv_123",
    turn_number=5,
    convergence_score=0.85
))
```

## Events

### TurnCompleteEvent

Emitted when a turn (A→B exchange) completes.

```python
@dataclass
class TurnCompleteEvent:
    conversation_id: str
    turn_number: int
    turn: Turn
    convergence_score: float
    timestamp: datetime = field(default_factory=datetime.now)
```

### MessageCompleteEvent

Emitted when an individual message completes.

```python
@dataclass
class MessageCompleteEvent:
    conversation_id: str
    agent_id: str
    message: Message
    duration_ms: int
    tokens_used: Optional[int]
    timestamp: datetime = field(default_factory=datetime.now)
```

### ConversationStartEvent

Emitted when a conversation begins.

```python
@dataclass
class ConversationStartEvent:
    conversation_id: str
    agent_a_model: str
    agent_b_model: str
    initial_prompt: str
    max_turns: int
    temperature_a: Optional[float]
    temperature_b: Optional[float]
    timestamp: datetime = field(default_factory=datetime.now)
```

### ConversationEndEvent

Emitted when a conversation ends.

```python
@dataclass
class ConversationEndEvent:
    conversation_id: str
    total_turns: int
    end_reason: str  # "max_turns", "convergence", "error", "stopped"
    final_convergence: float
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
```

## Types

### Agent

```python
class Agent(BaseModel):
    id: str
    model: str
    display_name: Optional[str] = None
    model_shortname: Optional[str] = None
    temperature: Optional[float] = None
```

### Message

```python
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
```

### Conversation

```python
class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    agents: List[Agent]
    messages: List[Message] = []
    started_at: datetime = Field(default_factory=datetime.now)
    initial_prompt: Optional[str] = None
```

### Turn

```python
@dataclass
class Turn:
    agent_a_message: Message
    agent_b_message: Message
    
    def as_messages(self) -> List[Message]:
        return [self.agent_a_message, self.agent_b_message]
```

## Rate Limiting

Pidgin includes built-in rate limiting to respect API limits.

```python
from pidgin.core.rate_limiter import StreamingRateLimiter

# Rate limiter is used internally by providers
rate_limiter = StreamingRateLimiter(
    calls_per_minute=60,
    calls_per_hour=1000
)
```

## Error Handling

All core APIs may raise the following exceptions:

- `ValueError`: Invalid configuration or parameters
- `RuntimeError`: System errors or resource issues
- `asyncio.TimeoutError`: Operation timeouts
- Provider-specific exceptions for API errors

Always wrap API calls in appropriate error handling:

```python
try:
    conversation = await conductor.run_conversation(...)
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```