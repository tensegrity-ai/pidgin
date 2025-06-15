from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass, field
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
    role: str  # "user" or "assistant"
    content: str
    agent_id: str  # Who sent the message (agent_a, agent_b, system, human, mediator)
    timestamp: datetime = Field(default_factory=datetime.now)


class Agent(BaseModel):
    id: str
    model: str
    display_name: Optional[str] = None
    model_shortname: Optional[str] = None  # Store the original model shortname


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    agents: List[Agent]
    messages: List[Message] = []
    started_at: datetime = Field(default_factory=datetime.now)
    initial_prompt: Optional[str] = None
