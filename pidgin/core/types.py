"""Core data types for Pidgin conversations.

This module defines the fundamental data structures used throughout Pidgin
for representing conversations, messages, agents, and turns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ConversationRole(str, Enum):
    """Distinguish conversation participants from external interventions."""

    AGENT_A = "agent_a"  # Conversation participant
    AGENT_B = "agent_b"  # Conversation participant


class InterventionSource(str, Enum):
    """External intervention sources (orthogonal to conversation)."""

    SYSTEM = "system"  # Technical/infrastructure messages
    HUMAN = "human"  # Researcher interventions
    MEDIATOR = "mediator"  # Neutral facilitation


@dataclass
class ConversationTurn:
    """Represents one complete A→B exchange with optional interventions."""

    agent_a_message: Optional["Message"] = None
    agent_b_message: Optional["Message"] = None
    post_turn_interventions: List["Message"] = field(default_factory=list)
    turn_number: int = 0

    @property
    def complete(self) -> bool:
        """True when both agents have responded."""
        return bool(self.agent_a_message and self.agent_b_message)

    @property
    def conversation_messages(self) -> List["Message"]:
        """Just the A↔B messages, excluding interventions."""
        messages = []
        if self.agent_a_message:
            messages.append(self.agent_a_message)
        if self.agent_b_message:
            messages.append(self.agent_b_message)
        return messages

    @property
    def all_messages(self) -> List["Message"]:
        """All messages including interventions."""
        return self.conversation_messages + self.post_turn_interventions


class Message(BaseModel):
    """Represents a single message in a conversation.

    Messages track both the content and metadata about who sent them
    and when. The role field follows OpenAI conventions ("user"/"assistant")
    while agent_id tracks the specific sender.

    Attributes:
        role: Either "user" or "assistant" following API conventions
        content: The actual text content of the message
        agent_id: Identifier of who sent the message (agent_a, agent_b, system, etc.)
        timestamp: When the message was created

    Example:
        msg = Message(
            role="assistant",
            content="Hello! How can I help?",
            agent_id="agent_a"
        )
    """

    role: str  # "user" or "assistant"
    content: str
    agent_id: str  # Who sent the message (agent_a, agent_b, system, human, mediator)
    timestamp: datetime = Field(default_factory=datetime.now)


class Agent(BaseModel):
    """Represents an AI agent in a conversation.

    Agents are the participants in conversations. Each agent has a specific
    model backing it and optional configuration like temperature.

    Attributes:
        id: Unique identifier (usually "agent_a" or "agent_b")
        model: Model identifier (e.g., "gpt-4", "claude-3-opus")
        display_name: Optional custom name for display
        model_display_name: Cached display name from model config
        temperature: Optional temperature override for this agent

    Example:
        agent = Agent(
            id="agent_a",
            model="claude-3-sonnet",
            display_name="Claude",
            temperature=0.7
        )
    """

    model_config = {"protected_namespaces": ()}

    id: str
    model: str
    display_name: Optional[str] = None
    model_display_name: Optional[str] = None  # Store the model display name from config
    temperature: Optional[float] = None  # Temperature setting for this agent
    thinking_enabled: Optional[bool] = None  # Enable extended thinking for this agent
    thinking_budget: Optional[int] = None  # Max thinking tokens for this agent


class Conversation(BaseModel):
    """Represents a complete conversation between agents.

    Conversations track all messages exchanged between agents along with
    metadata about when they occurred and what prompt initiated them.

    Attributes:
        id: Unique conversation identifier (auto-generated)
        agents: List of participating agents
        messages: All messages in chronological order
        started_at: When the conversation began
        initial_prompt: The prompt that started the conversation

    Example:
        conv = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt="Let's discuss philosophy"
        )
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    agents: List[Agent]
    messages: List[Message] = []
    started_at: datetime = Field(default_factory=datetime.now)
    initial_prompt: Optional[str] = None

    @property
    def agent_a(self) -> Optional[Agent]:
        return self.agents[0] if self.agents else None

    @property
    def agent_b(self) -> Optional[Agent]:
        return self.agents[1] if len(self.agents) > 1 else None

    @property
    def turn_count(self) -> int:
        # Each turn is 2 messages (agent_a then agent_b)
        return len(self.messages) // 2

    @property
    def start_time(self) -> float:
        return self.started_at.timestamp()
