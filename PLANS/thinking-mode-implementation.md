# Thinking Mode Implementation Plan (v2)

## Overview

Add support for extended thinking/reasoning traces in Pidgin. Models like Claude 3.5+ and OpenAI o-series can expose their reasoning process. This plan captures those traces as first-class data for analysis.

## Design Principles

1. **Use existing infrastructure**: `models.json` already has `extended_thinking` capability
2. **Additive schema changes**: New `thinking_traces` table, no changes to `messages`
3. **Event-driven**: New `ThinkingCompleteEvent` flows through existing event system
4. **Optional by default**: Thinking mode requires explicit opt-in via CLI flags
5. **Analysis-friendly**: Easy to include or exclude thinking from queries

---

## Phase 1: Database Schema

### 1.1 New Table: `thinking_traces`

**File**: `pidgin/database/schemas/thinking_traces.sql`

```sql
CREATE TABLE IF NOT EXISTS thinking_traces (
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    thinking_content TEXT NOT NULL,
    thinking_tokens INTEGER,
    duration_ms INTEGER,
    timestamp TIMESTAMP DEFAULT now(),
    PRIMARY KEY (conversation_id, turn_number, agent_id)
);

-- Index for efficient joins with messages
CREATE INDEX IF NOT EXISTS idx_thinking_traces_lookup
ON thinking_traces (conversation_id, turn_number, agent_id);
```

### 1.2 Repository: `ThinkingRepository`

**File**: `pidgin/database/repositories/thinking_repository.py`

```python
class ThinkingRepository(BaseRepository):
    async def insert_thinking_trace(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        thinking_content: str,
        thinking_tokens: Optional[int],
        duration_ms: Optional[int],
        timestamp: datetime
    ) -> None:
        ...

    async def get_thinking_for_conversation(
        self, conversation_id: str
    ) -> List[ThinkingTrace]:
        ...

    async def get_thinking_for_turn(
        self, conversation_id: str, turn_number: int, agent_id: str
    ) -> Optional[ThinkingTrace]:
        ...
```

### 1.3 EventStore Updates

**File**: `pidgin/database/event_store.py`

- Add `ThinkingRepository` to EventStore
- Add `import_thinking_events()` method for JSONL import
- Expose thinking queries through public API

---

## Phase 2: Event System

### 2.1 New Event: `ThinkingCompleteEvent`

**File**: `pidgin/core/events.py`

```python
@dataclass
class ThinkingCompleteEvent(Event):
    """Emitted when a model completes its thinking/reasoning phase."""
    conversation_id: str
    turn_number: int
    agent_id: str
    thinking_content: str
    thinking_tokens: Optional[int] = None
    duration_ms: Optional[int] = None
```

### 2.2 TrackingEventBus Handler

**File**: `pidgin/experiments/tracking_event_bus.py`

Add handler for `ThinkingCompleteEvent`:
- Write to JSONL (standard event flow)
- Update manifest with thinking token counts

### 2.3 PostProcessor Import

**File**: `pidgin/experiments/post_processor.py`

- Parse `ThinkingCompleteEvent` from JSONL
- Import to `thinking_traces` table via EventStore

---

## Phase 3: Provider Interface

### 3.1 Typed Response Chunks

**File**: `pidgin/providers/base.py`

```python
@dataclass
class ResponseChunk:
    """A chunk of response from a provider."""
    content: str
    chunk_type: Literal["thinking", "response"] = "response"


class Provider(ABC):
    @abstractmethod
    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None
    ) -> AsyncGenerator[ResponseChunk, None]:
        """Stream response chunks, optionally with thinking."""
        yield  # type: ignore
```

**Backward compatibility**: Update all providers to yield `ResponseChunk` instead of `str`. Non-thinking providers always yield `chunk_type="response"`.

### 3.2 Anthropic Provider

**File**: `pidgin/providers/anthropic.py`

```python
async def stream_response(
    self,
    messages: List[Message],
    temperature: Optional[float] = None,
    thinking_enabled: Optional[bool] = None,
    thinking_budget: Optional[int] = None
) -> AsyncGenerator[ResponseChunk, None]:

    api_params = {
        "model": self.model,
        "messages": conversation_messages,
        "max_tokens": 8192,
    }

    # Enable extended thinking for supported models
    if thinking_enabled:
        api_params["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget or 10000
        }

    async with self.client.messages.stream(**api_params) as stream:
        async for event in stream:
            if event.type == "content_block_delta":
                if hasattr(event.delta, "thinking"):
                    yield ResponseChunk(event.delta.thinking, "thinking")
                elif hasattr(event.delta, "text"):
                    yield ResponseChunk(event.delta.text, "response")
```

### 3.3 OpenAI Provider (o-series)

**File**: `pidgin/providers/openai.py`

```python
async def stream_response(...) -> AsyncGenerator[ResponseChunk, None]:
    params = {
        "model": self.model,
        "messages": openai_messages,
        "stream": True,
    }

    # o-series models use reasoning_effort
    if thinking_enabled and self._supports_reasoning():
        params["reasoning_effort"] = "high"

    # Note: OpenAI doesn't expose reasoning traces in API (yet)
    # This enables the mode but traces aren't returned
    async for chunk in response:
        yield ResponseChunk(chunk.content, "response")
```

### 3.4 Other Providers

Google, xAI, Ollama, Local, Silent:
- Accept `thinking_enabled` parameter (silent pass-through)
- Always yield `ResponseChunk` with `chunk_type="response"`
- Future: implement when providers add thinking support

### 3.5 EventAwareProvider Updates

**File**: `pidgin/providers/event_wrapper.py`

```python
async def handle_message_request(self, event: MessageRequestEvent):
    thinking_chunks: List[str] = []
    response_chunks: List[str] = []
    thinking_start: Optional[float] = None

    async for chunk in self.provider.stream_response(
        messages,
        temperature=event.temperature,
        thinking_enabled=event.thinking_enabled,
        thinking_budget=event.thinking_budget
    ):
        if chunk.chunk_type == "thinking":
            if not thinking_chunks:
                thinking_start = time.time()
            thinking_chunks.append(chunk.content)
            # Emit for live display
            await self.bus.emit(ThinkingChunkEvent(...))
        else:
            response_chunks.append(chunk.content)
            await self.bus.emit(MessageChunkEvent(...))

    # Emit thinking complete event
    if thinking_chunks:
        await self.bus.emit(ThinkingCompleteEvent(
            conversation_id=event.conversation_id,
            turn_number=event.turn_number,
            agent_id=event.agent_id,
            thinking_content="".join(thinking_chunks),
            thinking_tokens=self._count_tokens(thinking_chunks),
            duration_ms=int((time.time() - thinking_start) * 1000)
        ))

    # Emit message complete (unchanged)
    await self.bus.emit(MessageCompleteEvent(...))
```

---

## Phase 4: Configuration Flow

### 4.1 CLI Flags

**File**: `pidgin/cli/run.py`

```python
@click.option("--think", is_flag=True, help="Enable thinking mode for both agents")
@click.option("--think-a", is_flag=True, help="Enable thinking mode for agent A")
@click.option("--think-b", is_flag=True, help="Enable thinking mode for agent B")
@click.option("--think-budget", type=int, help="Max thinking tokens (default: 10000)")
```

### 4.2 Resolution Function

**File**: `pidgin/config/resolution.py`

```python
def resolve_thinking_config(
    think: bool,
    think_a: Optional[bool],
    think_b: Optional[bool],
    think_budget: Optional[int]
) -> Tuple[Optional[bool], Optional[bool], Optional[int]]:
    """Resolve thinking settings for both agents."""
    resolved_a = think_a if think_a is not None else (think or None)
    resolved_b = think_b if think_b is not None else (think or None)
    return resolved_a, resolved_b, think_budget
```

### 4.3 Agent Configuration

**File**: `pidgin/core/types.py`

```python
class Agent(BaseModel):
    model: str
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    thinking_enabled: Optional[bool] = None
    thinking_budget: Optional[int] = None
```

### 4.4 MessageRequestEvent

**File**: `pidgin/core/events.py`

```python
@dataclass
class MessageRequestEvent(Event):
    # Existing fields...
    thinking_enabled: Optional[bool] = None
    thinking_budget: Optional[int] = None
```

### 4.5 Model Capability Check

Use existing `models.json` infrastructure:

```python
from pidgin.config.model_loader import get_model_config

def supports_thinking(model_id: str) -> bool:
    config = get_model_config(model_id)
    return config.capabilities.extended_thinking if config else False
```

No hardcoded model lists - capabilities come from `models.json`.

---

## Phase 5: Display

### 5.1 Chat Display

**File**: `pidgin/cli/display/message_display.py`

```python
from pidgin.cli.constants import NORD_FROST_3

THINKING_STYLE = Style(color=NORD_FROST_3, italic=True, dim=True)
THINKING_PREFIX = "◇ "

def display_thinking_chunk(chunk: str, console: Console):
    """Display thinking content with distinct styling."""
    console.print(THINKING_PREFIX, style=THINKING_STYLE, end="")
    console.print(chunk, style=THINKING_STYLE, end="")

def display_thinking_complete(total_tokens: int, console: Console):
    """Display thinking summary after completion."""
    console.print(f"\n  [{total_tokens} thinking tokens]\n", style=THINKING_STYLE)
```

### 5.2 Tail Display

**File**: `pidgin/cli/tail.py`

Same styling as chat. When tailing JSONL:
- Parse `ThinkingCompleteEvent`
- Display thinking content with italic/dim style
- Show token count

### 5.3 Live Streaming

Add `ThinkingChunkEvent` for live display during streaming:

```python
@dataclass
class ThinkingChunkEvent(Event):
    """Emitted for each chunk of thinking content (for live display)."""
    conversation_id: str
    agent_id: str
    chunk: str
```

Subscribe in display components to show thinking as it streams.

---

## Phase 6: Monitor

### 6.1 Manifest Updates

**File**: `pidgin/experiments/manifest.py`

```python
# Token usage structure in manifest.json
{
    "token_usage": {
        "agent_a": {
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "thinking_tokens": 2100  # New field
        },
        "agent_b": {
            "prompt_tokens": 890,
            "completion_tokens": 432,
            "thinking_tokens": 0
        }
    }
}
```

### 6.2 Monitor Display

**File**: `pidgin/monitor/display_builder.py`

Show thinking tokens separately:

```
Agent A (claude-3.5-sonnet)
  Tokens: 1,801 (+2,100 thinking)

Agent B (gpt-4)
  Tokens: 1,322
```

Or in summary:
```
Total tokens: 5,223 (3,123 response + 2,100 thinking)
```

---

## Phase 7: Transcripts

### 7.1 Collapsible Thinking

**File**: `pidgin/experiments/transcript_generator.py`

```python
def format_turn_with_thinking(
    agent_name: str,
    model: str,
    thinking: Optional[ThinkingTrace],
    message: str
) -> str:
    lines = [f"**{agent_name}** ({model}):\n"]

    if thinking:
        lines.append("<details>")
        lines.append(f"<summary>◇ Thinking ({thinking.thinking_tokens} tokens)</summary>\n")
        lines.append(thinking.thinking_content)
        lines.append("\n</details>\n")

    lines.append(message)
    lines.append("\n---\n")

    return "\n".join(lines)
```

### 7.2 CLI Option for Inline Thinking

```python
@click.option("--inline-thinking", is_flag=True,
              help="Include thinking inline instead of collapsible")
```

For environments that don't render `<details>` tags:

```markdown
**Agent A** (claude-3.5-sonnet):

*◇ Thinking (847 tokens):*
*Let me consider how to approach this...*

The actual response here.
```

---

## Phase 8: YAML Spec Support

### 8.1 Experiment Spec

```yaml
name: thinking-experiment
agent_a: claude-3.5-sonnet
agent_b: gpt-4
turns: 10

# Thinking configuration
thinking: true           # Enable for both (if supported)
thinking_a: true         # Override for A
thinking_b: false        # Override for B
thinking_budget: 15000   # Max thinking tokens
```

### 8.2 Config Parsing

**File**: `pidgin/experiments/config.py`

```python
@dataclass
class ExperimentConfig:
    # Existing fields...
    thinking: Optional[bool] = None
    thinking_a: Optional[bool] = None
    thinking_b: Optional[bool] = None
    thinking_budget: Optional[int] = None
```

---

## Implementation Order

### Wave 1: Core Infrastructure
1. Add `ThinkingCompleteEvent` to events.py
2. Create `thinking_traces.sql` schema
3. Create `ThinkingRepository`
4. Update EventStore with thinking methods

### Wave 2: Provider Changes
5. Add `ResponseChunk` dataclass
6. Update `Provider` base interface
7. Update all providers to yield `ResponseChunk`
8. Implement thinking in Anthropic provider
9. Update `EventAwareProvider` to handle thinking chunks

### Wave 3: Configuration
10. Add CLI flags to run.py
11. Add resolution function
12. Update `Agent` and `MessageRequestEvent` with thinking fields
13. Wire through Conductor → MessageHandler → Provider

### Wave 4: Display & Storage
14. Add thinking display styles
15. Update chat display for thinking
16. Update tail display
17. Update TrackingEventBus to handle `ThinkingCompleteEvent`
18. Update manifest.json structure

### Wave 5: Post-Processing
19. Update PostProcessor to import thinking events
20. Update transcript generator with collapsible thinking
21. Add `--inline-thinking` option

### Wave 6: Testing & Polish
22. Unit tests for resolution, repository, events
23. Integration tests with local:test provider
24. Manual testing with Claude models
25. Update documentation

---

## Testing Strategy

### Unit Tests
- `test_resolve_thinking_config()` - flag resolution logic
- `test_thinking_repository()` - CRUD operations
- `test_response_chunk()` - chunk type handling

### Integration Tests
```python
async def test_thinking_event_flow():
    """Verify thinking flows from provider to database."""
    # Use mock provider that yields thinking chunks
    # Verify ThinkingCompleteEvent emitted
    # Verify thinking_traces table populated

async def test_thinking_disabled_by_default():
    """Verify no thinking when not requested."""
    # Run conversation without --think
    # Verify no ThinkingCompleteEvent emitted
```

### Manual Testing
```bash
# Test with thinking-capable model
pidgin chat -a claude-3-5-sonnet -b local:test --think-a

# Test with non-thinking model (silent pass-through)
pidgin chat -a gpt-4 -b local:test --think

# Test experiment with thinking
pidgin experiment run my-spec.yaml --think
```

---

## Design Decisions

### Thinking in Branching

**Decision**: No special handling required.

Message history sent to models doesn't include historical thinking traces - only the most recent thinking accompanies the response being generated. When branching:

1. Pick a branch point (a message turn)
2. New conversation continues from that message history
3. New responses generate their own thinking traces
4. Historical traces from original branch remain in database, keyed to original `conversation_id`

The `thinking_traces` table keys on `(conversation_id, turn_number, agent_id)` - branched conversations get new `conversation_id`s, so traces are naturally isolated.

### Token Costs

**Decision**: Include thinking tokens in cost calculations.

Thinking tokens consume API quota and should be reflected in cost estimates. The manifest tracks `thinking_tokens` separately, so include them in the cost formula alongside prompt and completion tokens.

### Thinking Truncation

**Decision**: No complex handling needed.

If thinking budget is exceeded, the API throws an error. We catch it, emit an error event, and the conversation stops at that turn. Any partial thinking that streamed before the error can be discarded (incomplete trace has limited value).

Natural recovery: branch from the previous turn with a higher `--think-budget`.

### Multi-block Thinking

**Decision**: Start with 1:1 (concatenate blocks).

Current providers (Anthropic) emit thinking as a single logical block. Store as concatenated content:

```
messages (1) ←→ (0..1) thinking_traces
```

If future models emit semantically distinct thinking phases, migrate to 1:n by adding a `block_index` column (additive change, existing rows default to 0). We preserve full content either way - just not internal structure we don't yet have a use for.

---

## Success Criteria

- [ ] `--think` flag works for supported models
- [ ] Thinking traces stored in separate table
- [ ] Thinking displayed distinctly in chat/tail
- [ ] Monitor shows thinking token counts
- [ ] Transcripts have collapsible thinking sections
- [ ] Non-thinking models silently ignore the flag
- [ ] No changes to existing `messages` table schema
- [ ] Existing queries/analysis unaffected
