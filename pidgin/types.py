from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str  # "user" or "assistant"  
    content: str
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Agent(BaseModel):
    id: str
    model: str


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    agents: List[Agent]
    messages: List[Message] = []
    started_at: datetime = Field(default_factory=datetime.now)
    initial_prompt: Optional[str] = None