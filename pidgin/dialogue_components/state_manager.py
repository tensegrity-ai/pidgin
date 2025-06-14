"""State manager for conversation state and checkpointing."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..types import Agent, Message
from ..checkpoint import ConversationState, CheckpointManager
from .base import Component


class StateManager(Component):
    """Manages conversation state and checkpointing."""

    def __init__(self):
        """Initialize state manager."""
        self.state: Optional[ConversationState] = None
        self.checkpoint_manager = CheckpointManager()
        self.checkpoint_enabled = True
        self.checkpoint_interval = 10

    def reset(self):
        """Reset state for new conversation."""
        self.state = None

    def initialize_state(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int,
        transcript_path: str,
    ) -> ConversationState:
        """Initialize conversation state for a new conversation.

        Args:
            agent_a: First agent
            agent_b: Second agent
            initial_prompt: Initial conversation prompt
            max_turns: Maximum number of turns
            transcript_path: Path for transcript saving

        Returns:
            Initialized conversation state
        """
        self.state = ConversationState(
            model_a=agent_a.model,
            model_b=agent_b.model,
            agent_a_id=agent_a.id,
            agent_b_id=agent_b.id,
            max_turns=max_turns,
            initial_prompt=initial_prompt,
            transcript_path=str(transcript_path),
        )
        return self.state

    def load_state(self, state: ConversationState):
        """Load an existing conversation state.

        Args:
            state: State to load
        """
        self.state = state

    def add_message(self, message: Message):
        """Add a message to the conversation state.

        Args:
            message: Message to add
        """
        if self.state:
            self.state.add_message(message)

    def increment_turn_count(self):
        """Increment the turn counter."""
        if self.state:
            self.state.turn_count += 1

    def save_checkpoint(self, force: bool = False) -> Optional[Path]:
        """Save current state to checkpoint.

        Args:
            force: Force checkpoint even if not at interval

        Returns:
            Path where checkpoint was saved, or None if not saved
        """
        if not self.state or not self.checkpoint_enabled:
            return None

        if force or self.state.turn_count % self.checkpoint_interval == 0:
            return self.state.save_checkpoint()

        return None

    def update_metadata(self, key: str, value: Any):
        """Update state metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        if self.state:
            self.state.metadata[key] = value

    def get_messages(self) -> List[Message]:
        """Get all conversation messages.

        Returns:
            List of messages
        """
        if self.state:
            return self.state.messages.copy()
        return []

    def get_turn_count(self) -> int:
        """Get current turn count.

        Returns:
            Current turn number
        """
        if self.state:
            return self.state.turn_count
        return 0

    def mark_paused(self):
        """Mark conversation as paused."""
        if self.state:
            self.state.pause_time = datetime.now()

    def set_checkpoint_config(self, enabled: bool, interval: int):
        """Update checkpoint configuration.

        Args:
            enabled: Whether checkpointing is enabled
            interval: Auto-save interval in turns
        """
        self.checkpoint_enabled = enabled
        self.checkpoint_interval = interval

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state.

        Returns:
            Dictionary with state information
        """
        if not self.state:
            return {}

        return {
            "turn_count": self.state.turn_count,
            "message_count": len(self.state.messages),
            "start_time": self.state.start_time.isoformat()
            if self.state.start_time
            else None,
            "pause_time": self.state.pause_time.isoformat()
            if self.state.pause_time
            else None,
            "model_a": self.state.model_a,
            "model_b": self.state.model_b,
            "has_metadata": bool(self.state.metadata),
        }
