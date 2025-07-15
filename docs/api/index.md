# Pidgin API Documentation

Pidgin provides a comprehensive Python API for programmatically running conversations, analyzing results, and extending functionality.

## Quick Start

```python
import asyncio
from pidgin.core import Conductor, Agent
from pidgin.providers.builder import build_provider

async def run_conversation():
    # Create agents
    agent_a = Agent(id="agent_a", model="claude-3-sonnet")
    agent_b = Agent(id="agent_b", model="gpt-4")
    
    # Initialize conductor
    conductor = Conductor(output_manager=None)
    
    # Run conversation
    conversation = await conductor.run_conversation(
        agent_a=agent_a,
        agent_b=agent_b,
        initial_prompt="Let's discuss the nature of consciousness",
        max_turns=10
    )
    
    # Access results
    for message in conversation.messages:
        print(f"{message.agent_id}: {message.content[:100]}...")

asyncio.run(run_conversation())
```

## Core Concepts

### Agents
Agents represent the AI models participating in conversations. Each agent has:
- A unique ID (typically "agent_a" or "agent_b")
- A model identifier (e.g., "claude-3-opus", "gpt-4")
- Optional configuration like temperature and display name

### Messages
Messages are the fundamental unit of communication. They contain:
- Role ("user" or "assistant" following API conventions)
- Content (the actual text)
- Agent ID (who sent the message)
- Timestamp

### Conversations
Conversations are collections of messages between agents, including:
- The participating agents
- All messages in chronological order
- Metadata like start time and initial prompt

### Providers
Providers implement the interface to specific AI model APIs. Pidgin includes providers for:
- OpenAI (GPT models)
- Anthropic (Claude models)
- Google (Gemini models)
- xAI (Grok models)
- Local models (via Ollama)

## API Modules

- [Core APIs](core.md) - Conversation orchestration and management
- [Provider APIs](providers.md) - AI model integrations
- [Metrics APIs](metrics.md) - Conversation analysis and metrics
- [Experiment APIs](experiments.md) - Multi-conversation experiments
- [Analysis APIs](analysis.md) - Data export and visualization

## Architecture

Pidgin follows an event-driven architecture where all significant actions emit events to a central event bus. This enables:

- Complete audit trails via JSONL logs
- Loose coupling between components
- Easy extension through event listeners
- Robust experiment resumption

## Type Safety

Pidgin uses type hints throughout the codebase. For type checking:

```bash
pip install mypy
mypy pidgin/
```

## Extending Pidgin

### Custom Providers

```python
from pidgin.providers.base import Provider
from typing import List, AsyncGenerator, Optional
from pidgin.core.types import Message

class MyCustomProvider(Provider):
    async def stream_response(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        # Your implementation here
        response = await self.call_my_api(messages)
        for chunk in response:
            yield chunk
```

### Event Listeners

```python
from pidgin.core.events import TurnCompleteEvent

async def on_turn_complete(event: TurnCompleteEvent):
    print(f"Turn {event.turn_number} complete!")
    print(f"Convergence: {event.convergence_score}")

# Register with event bus
bus.subscribe(TurnCompleteEvent, on_turn_complete)
```

## Best Practices

1. **Use async/await**: All core APIs are asynchronous for better performance
2. **Handle errors**: Providers may raise exceptions for rate limits or API errors
3. **Monitor convergence**: Use convergence scores to detect conversation patterns
4. **Leverage events**: Subscribe to events for custom analysis or interventions
5. **Type your code**: Use type hints for better IDE support and error catching

## Further Reading

- [Examples](https://github.com/nicholas-lange/pidgin/tree/main/examples) - Code examples
- [Architecture](../ARCHITECTURE.md) - System architecture overview
- [Contributing](../CONTRIBUTING.md) - How to contribute to Pidgin