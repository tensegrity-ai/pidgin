from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, Tuple

from .types import Conversation, Message


class Router(Protocol):
    """Router interface for future extensibility"""

    async def stream_response(
        self, messages: List[Message]
    ) -> AsyncIterator[str]:
        ...

    async def get_next_response(
        self, conversation_history: List[Message], target_agent: str
    ) -> Message:
        ...

    async def get_next_response_stream(
        self, conversation_history: List[Message], target_agent: str
    ) -> AsyncIterator[Tuple[str, str]]:
        ...


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
        agent_messages = self._build_agent_history(
            conversation_history, target_agent
        )

        # Get provider response - use streaming and collect all chunks
        provider = self.providers[target_agent]
        chunks = []
        async for chunk in provider.stream_response(agent_messages):
            chunks.append(chunk)
        response_text = ''.join(chunks)

        return Message(
            role="assistant", content=response_text, agent_id=target_agent
        )

    async def get_next_response_stream(
        self, conversation_history: List[Message], target_agent: str
    ) -> AsyncIterator[Tuple[str, str]]:
        """Stream response chunks from target agent.

        Yields (chunk, agent_id) tuples.
        """

        # Build message history for target agent (A↔B messages only)
        agent_messages = self._build_agent_history(
            conversation_history, target_agent
        )

        # Get provider response
        provider = self.providers[target_agent]

        async for chunk in provider.stream_response(agent_messages):
            yield chunk, target_agent

    def _build_agent_history(
        self, messages: List[Message], target_agent: str
    ) -> List[Message]:
        """Build conversation history from target agent's perspective.

        Two types of messages:
        1. Agent messages (agent_a, agent_b) - normal conversation flow
        2. Everything else - researcher interventions clearly marked
        """
        agent_history = []

        for msg in messages:
            # Researcher interventions (anything not from agents)
            if msg.agent_id not in ["agent_a", "agent_b"]:
                # Mark ALL non-agent messages as researcher guidance
                marked_content = f"[RESEARCHER NOTE]: {msg.content}"
                agent_history.append(
                    Message(
                        role="user",
                        content=marked_content,
                        agent_id=msg.agent_id
                    )
                )
            # Target agent's own messages
            elif msg.agent_id == target_agent:
                agent_history.append(
                    Message(
                        role="assistant",
                        content=msg.content,
                        agent_id=msg.agent_id
                    )
                )
            # Other agent's messages
            else:
                agent_history.append(
                    Message(
                        role="user",
                        content=msg.content,
                        agent_id=msg.agent_id
                    )
                )

        return agent_history

    # Legacy method for backward compatibility during transition
    async def route_message(
        self, message: Message, conversation: Conversation
    ) -> Message:
        """Legacy method - determine next agent and get response."""
        # Determine target agent based on who spoke last
        if self.last_agent_id is None or self.last_agent_id == "agent_b":
            target_agent_id = "agent_a"
        else:
            target_agent_id = "agent_b"

        # Update last agent tracker
        self.last_agent_id = target_agent_id

        return await self.get_next_response(
            conversation.messages, target_agent_id
        )
