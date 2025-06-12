from typing import Protocol, List
from .types import Message, Conversation, ConversationRole


class Router(Protocol):
    """Router interface for future extensibility"""

    async def get_next_response(
        self, conversation_history: List[Message], target_agent: str
    ) -> Message:
        ...


class DirectRouter:
    """Simplified router: clean A↔B alternation only."""

    def __init__(self, providers: dict):
        self.providers = providers
        self.last_agent_id = None

    async def get_next_response(
        self, conversation_history: List[Message], target_agent: str
    ) -> Message:
        """Get response from target agent given conversation history."""

        # Build message history for target agent (A↔B messages only)
        agent_messages = self._build_agent_history(conversation_history, target_agent)

        # Get provider response
        provider = self.providers[target_agent]
        response_text = await provider.get_response(agent_messages)

        return Message(role="assistant", content=response_text, agent_id=target_agent)

    def _build_agent_history(
        self, messages: List[Message], target_agent: str
    ) -> List[Message]:
        """Build conversation history from target agent's perspective."""
        # Only include A↔B conversation messages, exclude interventions
        conversation_messages = [
            msg
            for msg in messages
            if msg.agent_id
            in [ConversationRole.AGENT_A, ConversationRole.AGENT_B, "system"]
        ]

        # Convert to agent's perspective (user/assistant alternation)
        agent_history = []
        for msg in conversation_messages:
            if msg.agent_id == "system":
                # System messages (like initial prompt) are always user role
                agent_history.append(
                    Message(role="user", content=msg.content, agent_id=msg.agent_id)
                )
            elif msg.agent_id == target_agent:
                # Agent's own messages are assistant role
                agent_history.append(
                    Message(
                        role="assistant", content=msg.content, agent_id=msg.agent_id
                    )
                )
            else:
                # Other agent's messages are user role
                agent_history.append(
                    Message(role="user", content=msg.content, agent_id=msg.agent_id)
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

        return await self.get_next_response(conversation.messages, target_agent_id)
