"""Refactored EventStore using repository pattern.

This is a new implementation that delegates to specialized repositories
while maintaining backward compatibility with the existing EventStore interface.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from .repositories import (
    EventRepository,
    ExperimentRepository,
    ConversationRepository,
    MessageRepository,
    MetricsRepository
)
from .async_duckdb import AsyncDuckDB
from ..core.events import Event
from ..core.types import Agent, Conversation, ConversationTurn
from ..io.logger import get_logger

logger = get_logger("event_store_refactored")


class RefactoredEventStore:
    """Refactored EventStore using repository pattern for better separation of concerns."""
    
    def __init__(self, db: AsyncDuckDB):
        """Initialize with database connection and repositories.
        
        Args:
            db: AsyncDuckDB connection
        """
        self.db = db
        
        # Initialize repositories
        self.events = EventRepository(db)
        self.experiments = ExperimentRepository(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.metrics = MetricsRepository(db)
        
        logger.info("Initialized RefactoredEventStore with repository pattern")
    
    # Event operations (delegate to EventRepository)
    async def save_event(self, event: Event, experiment_id: str, conversation_id: str):
        """Save an event to the database."""
        await self.events.save_event(event, experiment_id, conversation_id)
    
    async def get_events(
        self,
        experiment_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get events with optional filters."""
        return await self.events.get_events(
            experiment_id=experiment_id,
            conversation_id=conversation_id,
            event_type=event_type,
            limit=limit
        )
    
    # Experiment operations (delegate to ExperimentRepository)
    async def create_experiment(self, experiment_id: str, config: dict):
        """Create a new experiment."""
        await self.experiments.create_experiment(experiment_id, config)
    
    async def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID."""
        return await self.experiments.get_experiment(experiment_id)
    
    async def update_experiment_status(
        self,
        experiment_id: str,
        status: str,
        end_reason: Optional[str] = None
    ):
        """Update experiment status."""
        await self.experiments.update_experiment_status(
            experiment_id, status, end_reason
        )
    
    async def list_experiments(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filters."""
        return await self.experiments.list_experiments(status_filter, limit)
    
    # Conversation operations (delegate to ConversationRepository)
    async def create_conversation(
        self,
        experiment_id: str,
        conversation_id: str,
        config: dict
    ):
        """Create a new conversation."""
        await self.conversations.create_conversation(
            experiment_id, conversation_id, config
        )
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        return await self.conversations.get_conversation(conversation_id)
    
    async def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
        end_reason: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update conversation status."""
        await self.conversations.update_conversation_status(
            conversation_id, status, end_reason, error_message
        )
    
    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get message history for a conversation."""
        return await self.conversations.get_conversation_history(conversation_id)
    
    async def log_agent_name(
        self,
        conversation_id: str,
        agent_id: str,
        chosen_name: str,
        turn_number: int = 0
    ):
        """Log agent's chosen name."""
        await self.conversations.log_agent_name(
            conversation_id, agent_id, chosen_name, turn_number
        )
    
    async def get_agent_names(self, conversation_id: str) -> Dict[str, str]:
        """Get agent names for a conversation."""
        return await self.conversations.get_agent_names(conversation_id)
    
    # Message operations (delegate to MessageRepository)
    async def save_message(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None
    ):
        """Save a message."""
        await self.messages.save_message(
            conversation_id, turn_number, agent_id, role, content, tokens_used
        )
    
    async def get_turn_messages(
        self,
        conversation_id: str,
        turn_number: int
    ) -> List[Dict[str, Any]]:
        """Get all messages for a turn."""
        return await self.messages.get_turn_messages(conversation_id, turn_number)
    
    # Metrics operations (delegate to MetricsRepository)
    async def log_turn_metrics(
        self,
        conversation_id: str,
        turn_number: int,
        metrics: Dict[str, Any]
    ):
        """Log metrics for a turn."""
        await self.metrics.log_turn_metrics(conversation_id, turn_number, metrics)
    
    async def log_message_metrics(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        message_length: int,
        vocabulary_size: int,
        punctuation_ratio: float,
        sentiment_score: Optional[float] = None
    ):
        """Log metrics for a message."""
        await self.metrics.log_message_metrics(
            conversation_id, turn_number, agent_id, message_length,
            vocabulary_size, punctuation_ratio, sentiment_score
        )
    
    async def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for an experiment."""
        return await self.metrics.get_experiment_metrics(experiment_id)
    
    async def calculate_convergence_metrics(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Calculate convergence metrics."""
        return await self.metrics.calculate_convergence_metrics(conversation_id)
    
    # Token usage operations (kept simple for now)
    async def log_token_usage(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int
    ):
        """Log token usage."""
        query = """
            INSERT INTO token_usage (
                conversation_id, turn_number, agent_id, model,
                input_tokens, output_tokens, total_tokens, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            conversation_id, turn_number, agent_id, model,
            input_tokens, output_tokens, total_tokens, datetime.now()
        )
        await self.db.execute(query, params)
    
    # Cleanup operations
    async def delete_experiment(self, experiment_id: str):
        """Delete an experiment and all related data."""
        # Get all conversations
        conversations = await self.conversations.list_conversations_by_experiment(
            experiment_id
        )
        
        # Delete each conversation
        for conv in conversations:
            await self.delete_conversation(conv["conversation_id"])
        
        # Delete experiment
        await self.experiments.delete_experiment(experiment_id)
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all related data."""
        # Delete metrics
        await self.metrics.delete_metrics(conversation_id)
        
        # Delete messages
        await self.messages.delete_messages(conversation_id)
        
        # Delete conversation (includes events, agent names, etc.)
        await self.conversations.delete_conversation(conversation_id)
    
    # Backward compatibility methods
    async def get_conversation_agent_configs(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get agent configurations for a conversation."""
        conv = await self.get_conversation(conversation_id)
        if conv and "config" in conv:
            config = conv["config"]
            if isinstance(config, dict):
                return {
                    "agent_a": config.get("agent_a", {}),
                    "agent_b": config.get("agent_b", {})
                }
        return None
    
    async def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get summary statistics for an experiment."""
        exp = await self.get_experiment(experiment_id)
        if not exp:
            return {}
        
        # Get conversation stats
        conversations = await self.conversations.list_conversations_by_experiment(
            experiment_id
        )
        
        completed = sum(1 for c in conversations if c["status"] == "completed")
        failed = sum(1 for c in conversations if c["status"] == "failed")
        running = sum(1 for c in conversations if c["status"] == "running")
        
        # Get metrics
        metrics = await self.get_experiment_metrics(experiment_id)
        
        return {
            "experiment_id": experiment_id,
            "status": exp["status"],
            "total_conversations": len(conversations),
            "completed": completed,
            "failed": failed,
            "running": running,
            "started_at": exp.get("started_at"),
            "ended_at": exp.get("ended_at"),
            **metrics
        }