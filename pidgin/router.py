from typing import Protocol
from .types import Message, Conversation


class Router(Protocol):
    """Router interface for future extensibility"""
    async def route_message(
        self, 
        message: Message, 
        conversation: Conversation
    ) -> Message:
        ...


class DirectRouter:
    """Simple router that sends messages directly between agents"""
    def __init__(self, providers: dict):
        self.providers = providers
        self.last_agent_id = None
    
    async def route_message(
        self, 
        message: Message, 
        conversation: Conversation
    ) -> Message:
        # Determine target agent based on who spoke last
        if self.last_agent_id is None or self.last_agent_id == "agent_b":
            target_agent_id = "agent_a"
        else:
            target_agent_id = "agent_b"
        
        # Update last agent tracker
        self.last_agent_id = target_agent_id
        
        # Get provider for target agent
        target_agent = next(a for a in conversation.agents if a.id == target_agent_id)
        provider = self.providers[target_agent_id]
        
        # Build message history for the target agent
        # For the agent, messages should alternate: user, assistant, user, assistant...
        agent_messages = []
        for msg in conversation.messages:
            if msg.agent_id == "system":
                # Initial prompt is always from user
                agent_messages.append(Message(
                    role="user",
                    content=msg.content,
                    agent_id=msg.agent_id
                ))
            elif msg.agent_id == target_agent_id:
                # Agent's own messages are assistant
                agent_messages.append(Message(
                    role="assistant",
                    content=msg.content,
                    agent_id=msg.agent_id
                ))
            else:
                # Other agent's messages are user
                agent_messages.append(Message(
                    role="user",
                    content=msg.content,
                    agent_id=msg.agent_id
                ))
        
        # Get response
        response_text = await provider.get_response(agent_messages)
        
        # Create response message
        return Message(
            role="assistant",
            content=response_text,
            agent_id=target_agent_id
        )