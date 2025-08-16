from collections.abc import AsyncIterator
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .types import Message


class Router(Protocol):
    """Router interface for future extensibility"""

    async def stream_response(self, messages: List[Message]) -> AsyncIterator[str]: ...

    async def get_next_response(
        self, conversation_history: List[Message], target_agent: str
    ) -> Message: ...

    async def get_next_response_stream(
        self, conversation_history: List[Message], target_agent: str
    ) -> AsyncIterator[Tuple[str, str]]: ...


class DirectRouter:
    """Simplified router: clean A↔B alternation only."""

    def __init__(self, providers: Dict[str, Any]):
        self.providers = providers
        self.last_agent_id: Optional[str] = None

    async def get_next_response(
        self, conversation_history: List[Message], target_agent: str
    ) -> Message:
        """Get response from target agent given conversation history."""

        # Build message history for target agent (A↔B messages only)
        agent_messages = self._build_agent_history(conversation_history, target_agent)

        # Get provider response - use streaming and collect all chunks
        provider = self.providers[target_agent]
        chunks = []
        async for chunk in provider.stream_response(agent_messages):
            chunks.append(chunk)
        response_text = "".join(chunks)

        return Message(role="assistant", content=response_text, agent_id=target_agent)

    async def get_next_response_stream(
        self, conversation_history: List[Message], target_agent: str
    ) -> AsyncIterator[Tuple[str, str]]:
        """Stream response chunks from target agent.

        Yields (chunk, agent_id) tuples.
        """

        # Build message history for target agent (A↔B messages only)
        agent_messages = self._build_agent_history(conversation_history, target_agent)

        # Get provider response
        provider = self.providers[target_agent]

        async for chunk in provider.stream_response(agent_messages):
            yield chunk, target_agent

    def _build_agent_history(
        self, messages: List[Message], target_agent: str
    ) -> List[Message]:
        """Build conversation history from target agent's perspective.

        Three types of messages:
        1. System messages - role clarification
        2. Agent messages (agent_a, agent_b) - normal conversation flow
        3. Everything else - human interventions clearly marked
        """
        agent_history = []

        for msg in messages:
            # System messages get special handling
            if msg.agent_id == "system":
                # For choose names mode, use the same system prompt for both agents
                if "Please choose a short name" in msg.content:
                    # This is a choose-names prompt, use as-is for both agents
                    agent_history.append(
                        Message(
                            role="system", content=msg.content, agent_id=msg.agent_id
                        )
                    )
                else:
                    # Adjust the content for Agent B
                    if target_agent == "agent_b":
                        adjusted_content = msg.content.replace(
                            "You are Agent A", "You are Agent B"
                        ).replace(
                            "Your conversation partner (Agent B)",
                            "Your conversation partner (Agent A)",
                        )
                        # Also handle model-specific names
                        adjusted_content = adjusted_content.replace(
                            "You are Sonnet-1", "You are Sonnet-2"
                        ).replace(
                            "Your conversation partner (Sonnet-2)",
                            "Your conversation partner (Sonnet-1)",
                        )
                        agent_history.append(
                            Message(
                                role="system",
                                content=adjusted_content,
                                agent_id=msg.agent_id,
                            )
                        )
                    else:
                        agent_history.append(
                            Message(
                                role="system",
                                content=msg.content,
                                agent_id=msg.agent_id,
                            )
                        )
            # Target agent's own messages
            elif msg.agent_id == target_agent:
                agent_history.append(
                    Message(
                        role="assistant", content=msg.content, agent_id=msg.agent_id
                    )
                )
            # Other agent's messages
            elif msg.agent_id in ["agent_a", "agent_b"]:
                agent_history.append(
                    Message(role="user", content=msg.content, agent_id=msg.agent_id)
                )
            # Any other message (including initial prompt) passes through as user message
            else:
                agent_history.append(
                    Message(role="user", content=msg.content, agent_id=msg.agent_id)
                )

        return agent_history
