"""Base LLM interface for all language model implementations."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator, Union
from dataclasses import dataclass
from datetime import datetime
import uuid

from pidgin.config.archetypes import Archetype, ArchetypeConfig


@dataclass
class Message:
    """Represents a message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    model: str
    usage: Dict[str, int]  # tokens used, etc.
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    """Configuration for an LLM instance."""
    model: str
    archetype: Union[Archetype, ArchetypeConfig]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    system_prompt: Optional[str] = None
    
    @property
    def archetype_config(self) -> ArchetypeConfig:
        """Get archetype configuration."""
        if isinstance(self.archetype, ArchetypeConfig):
            return self.archetype
        from pidgin.config.archetypes import get_archetype_config
        return get_archetype_config(self.archetype)


class LLM(ABC):
    """Abstract base class for language model implementations."""
    
    def __init__(self, config: LLMConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key
        self.id = str(uuid.uuid4())
        self._conversation_history: List[Message] = []
        
        # Apply archetype configuration
        archetype_config = config.archetype_config
        if config.temperature is None:
            config.temperature = archetype_config.temperature
        if config.top_p is None:
            config.top_p = archetype_config.top_p
        if config.system_prompt is None:
            config.system_prompt = archetype_config.system_prompt
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """Return the provider name (e.g., 'anthropic', 'openai')."""
        pass
    
    @property
    def name(self) -> str:
        """Return a friendly name for this LLM instance."""
        archetype_name = self.config.archetype_config.name
        return f"{self.config.model} ({archetype_name})"
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncIterator[str]]:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate that the LLM connection is working."""
        pass
    
    def add_to_history(self, message: Message):
        """Add a message to conversation history."""
        self._conversation_history.append(message)
    
    def get_history(self) -> List[Message]:
        """Get conversation history."""
        return self._conversation_history.copy()
    
    def clear_history(self):
        """Clear conversation history."""
        self._conversation_history.clear()
    
    def prepare_messages(self, messages: List[Message]) -> List[Message]:
        """Prepare messages for the API, including system prompt."""
        prepared = []
        
        # Add system prompt if configured
        if self.config.system_prompt:
            prepared.append(Message(
                role="system",
                content=self.config.system_prompt
            ))
        
        # Add provided messages
        prepared.extend(messages)
        
        return prepared
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Simple estimation: ~4 characters per token
        # Override in specific implementations for accurate counting
        return len(text) // 4
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"