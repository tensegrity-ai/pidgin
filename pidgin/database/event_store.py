"""EventStore - synchronous database interface with JSONL import.

This is the primary database interface for Pidgin, providing synchronous
access to all experiment, conversation, and metrics data.
"""

import json
import duckdb
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..core.events import Event
from ..core.types import Agent, Conversation, ConversationTurn
from ..io.logger import get_logger

logger = get_logger("event_store")


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    experiment_id: str
    events_imported: int
    conversations_imported: int
    error: Optional[str] = None
    duration_seconds: float = 0.0


class EventStore:
    """EventStore - primary database interface for Pidgin.
    
    Provides synchronous access to experiments, conversations, metrics,
    and JSONL import functionality.
    """
    
    def __init__(self, db_path: Path):
        """Initialize with direct DuckDB connection.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.db = duckdb.connect(str(db_path))
        self._ensure_schema()
        
        logger.info(f"Initialized EventStore with database: {db_path}")
    
    def _ensure_schema(self):
        """Ensure database schema exists."""
        from .schema import (
            EVENT_SCHEMA, EXPERIMENTS_SCHEMA, CONVERSATIONS_SCHEMA, 
            TURN_METRICS_SCHEMA, MESSAGES_SCHEMA, TOKEN_USAGE_SCHEMA
        )
        
        # Create all tables
        self.db.execute(EVENT_SCHEMA)
        self.db.execute(EXPERIMENTS_SCHEMA)
        self.db.execute(CONVERSATIONS_SCHEMA)
        self.db.execute(TURN_METRICS_SCHEMA)
        self.db.execute(MESSAGES_SCHEMA)
        self.db.execute(TOKEN_USAGE_SCHEMA)
        
        logger.info("Database schema ensured")
    
    def close(self):
        """Close database connection."""
        if hasattr(self, 'db') and self.db:
            self.db.close()
    
    # Event Operations
    def save_event(self, event: Event, experiment_id: str, conversation_id: str):
        """Save an event to the database.
        
        Args:
            event: Event to save
            experiment_id: Experiment ID
            conversation_id: Conversation ID
        """
        query = """
            INSERT INTO events (
                timestamp, event_type, conversation_id, 
                experiment_id, event_data, sequence
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        # Get next sequence number for this conversation
        seq_result = self.db.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE conversation_id = ?",
            [conversation_id]
        ).fetchone()
        sequence = seq_result[0] if seq_result else 1
        
        # Convert event to dict for storage
        event_dict = {
            "event_type": event.__class__.__name__,
            "conversation_id": conversation_id,
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id
        }
        
        # Add event-specific fields
        for field_name in event.__dataclass_fields__:
            if field_name not in ["timestamp", "event_id"]:
                value = getattr(event, field_name)
                if hasattr(value, "isoformat"):
                    event_dict[field_name] = value.isoformat()
                elif hasattr(value, "__dict__"):
                    event_dict[field_name] = value.__dict__
                else:
                    event_dict[field_name] = value
        
        self.db.execute(query, [
            event.timestamp,
            event.__class__.__name__,
            conversation_id,
            experiment_id,
            json.dumps(event_dict),
            sequence
        ])
        
        logger.debug(f"Saved {event.__class__.__name__} for conversation {conversation_id}")
    
    def get_events(
        self,
        conversation_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get events with optional filters.
        
        Args:
            conversation_id: Filter by conversation
            experiment_id: Filter by experiment
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of event dictionaries
        """
        conditions = []
        params = []
        
        if conversation_id:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)
        
        if experiment_id:
            conditions.append("experiment_id = ?")
            params.append(experiment_id)
        
        if event_types:
            placeholders = ",".join(["?" for _ in event_types])
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(event_types)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT event_data 
            FROM events 
            {where_clause}
            ORDER BY timestamp, sequence
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        result = self.db.execute(query, params).fetchall()
        
        events = []
        for row in result:
            event_data = json.loads(row[0])
            events.append(event_data)
        
        return events
    
    # Experiment Operations
    def create_experiment(self, name: str, config: dict) -> str:
        """Create a new experiment.
        
        Args:
            name: Experiment name
            config: Experiment configuration
            
        Returns:
            Experiment ID
        """
        experiment_id = uuid.uuid4().hex
        created_at = datetime.now()
        
        query = """
            INSERT INTO experiments (
                experiment_id, name, config, status, 
                created_at, total_conversations, completed_conversations,
                failed_conversations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute(query, [
            experiment_id,
            name,
            json.dumps(config),
            "created",
            created_at,
            0,  # total_conversations
            0,  # completed_conversations 
            0   # failed_conversations
        ])
        
        logger.info(f"Created experiment {experiment_id}: {name}")
        return experiment_id
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment data as dict or None
        """
        result = self.db.execute(
            "SELECT * FROM experiments WHERE experiment_id = ?",
            [experiment_id]
        ).fetchone()
        
        if result:
            cols = [desc[0] for desc in self.db.description]
            exp_dict = dict(zip(cols, result))
            
            # Parse JSON fields
            if 'config' in exp_dict and exp_dict['config']:
                try:
                    exp_dict['config'] = json.loads(exp_dict['config'])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse config for experiment {experiment_id}")
            
            if 'metadata' in exp_dict and exp_dict['metadata']:
                try:
                    exp_dict['metadata'] = json.loads(exp_dict['metadata'])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse metadata for experiment {experiment_id}")
            
            return exp_dict
        
        return None
    
    def update_experiment_status(self, experiment_id: str, status: str, 
                               ended_at: Optional[datetime] = None):
        """Update experiment status.
        
        Args:
            experiment_id: Experiment ID
            status: New status
            ended_at: Optional end timestamp
        """
        if ended_at:
            query = """
                UPDATE experiments 
                SET status = ?, completed_at = ? 
                WHERE experiment_id = ?
            """
            params = [status, ended_at, experiment_id]
        else:
            query = "UPDATE experiments SET status = ? WHERE experiment_id = ?"
            params = [status, experiment_id]
        
        self.db.execute(query, params)
        logger.info(f"Updated experiment {experiment_id} status to {status}")
    
    def list_experiments(self, status_filter: Optional[str] = None, 
                        limit: int = 50) -> List[Dict[str, Any]]:
        """List experiments with optional filters.
        
        Args:
            status_filter: Optional status to filter by
            limit: Maximum number of results
            
        Returns:
            List of experiment dicts
        """
        if status_filter:
            query = """
                SELECT * FROM experiments 
                WHERE status = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
            params = [status_filter, limit]
        else:
            query = """
                SELECT * FROM experiments 
                ORDER BY created_at DESC 
                LIMIT ?
            """
            params = [limit]
        
        results = self.db.execute(query, params).fetchall()
        
        if not results:
            return []
        
        # Get column names
        cols = [desc[0] for desc in self.db.description]
        
        experiments = []
        for row in results:
            exp_dict = dict(zip(cols, row))
            
            # Parse JSON fields
            if 'config' in exp_dict and exp_dict['config']:
                try:
                    exp_dict['config'] = json.loads(exp_dict['config'])
                except json.JSONDecodeError:
                    pass
            
            if 'metadata' in exp_dict and exp_dict['metadata']:
                try:
                    exp_dict['metadata'] = json.loads(exp_dict['metadata'])
                except json.JSONDecodeError:
                    pass
            
            experiments.append(exp_dict)
        
        return experiments
    
    # Conversation Operations
    def create_conversation(self, experiment_id: str, conversation_id: str, config: dict):
        """Create a new conversation.
        
        Args:
            experiment_id: Experiment ID
            conversation_id: Conversation ID
            config: Conversation configuration
        """
        query = """
            INSERT INTO conversations (
                conversation_id, experiment_id, status, created_at,
                agent_a_model, agent_a_provider, agent_a_temperature,
                agent_b_model, agent_b_provider, agent_b_temperature,
                max_turns, initial_prompt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Extract config values
        agent_a_config = config.get("agent_a", {})
        agent_b_config = config.get("agent_b", {})
        
        self.db.execute(query, [
            conversation_id,
            experiment_id,
            "created",
            datetime.now(),
            agent_a_config.get("model", "unknown"),
            agent_a_config.get("provider", "unknown"),
            agent_a_config.get("temperature", 0.7),
            agent_b_config.get("model", "unknown"),
            agent_b_config.get("provider", "unknown"),
            agent_b_config.get("temperature", 0.7),
            config.get("max_turns", 25),
            config.get("initial_prompt", "")
        ])
        
        logger.debug(f"Created conversation {conversation_id} for experiment {experiment_id}")
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation data as dict or None
        """
        result = self.db.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?",
            [conversation_id]
        ).fetchone()
        
        if result:
            cols = [desc[0] for desc in self.db.description]
            return dict(zip(cols, result))
        
        return None
    
    def update_conversation_status(self, conversation_id: str, status: str,
                                 end_reason: Optional[str] = None,
                                 error_message: Optional[str] = None):
        """Update conversation status.
        
        Args:
            conversation_id: Conversation ID
            status: New status
            end_reason: Optional end reason
            error_message: Optional error message
        """
        if status == "completed" or status == "failed":
            # Calculate final metrics if completing
            final_score = None
            total_turns = 0
            if status == "completed":
                # Get the final convergence score from turn metrics
                result = self.db.execute("""
                    SELECT turn_number, convergence_score
                    FROM turn_metrics
                    WHERE conversation_id = ?
                    ORDER BY turn_number DESC
                    LIMIT 1
                """, [conversation_id]).fetchone()
                
                if result:
                    total_turns = result[0]
                    final_score = result[1]
            
            query = """
                UPDATE conversations 
                SET status = ?, completed_at = ?, convergence_reason = ?, 
                    error_message = ?, final_convergence_score = ?, total_turns = ?
                WHERE conversation_id = ?
            """
            params = [status, datetime.now(), end_reason, error_message, 
                     final_score, total_turns, conversation_id]
        else:
            query = "UPDATE conversations SET status = ? WHERE conversation_id = ?"
            params = [status, conversation_id]
        
        self.db.execute(query, params)
        logger.debug(f"Updated conversation {conversation_id} status to {status}")
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get message history for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of message dicts ordered by turn and agent
        """
        query = """
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY turn_number, agent_id
        """
        
        results = self.db.execute(query, [conversation_id]).fetchall()
        
        if not results:
            return []
        
        cols = [desc[0] for desc in self.db.description]
        return [dict(zip(cols, row)) for row in results]
    
    # Agent Name Operations
    def log_agent_name(self, conversation_id: str, agent_id: str, 
                      chosen_name: str, turn_number: int = 0):
        """Log agent's chosen name.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID (agent_a or agent_b)
            chosen_name: Chosen name
            turn_number: Turn number (default 0)
        """
        # Update the conversation with the chosen name
        if agent_id == "agent_a":
            column = "agent_a_chosen_name"
        elif agent_id == "agent_b":
            column = "agent_b_chosen_name"
        else:
            logger.warning(f"Unknown agent_id: {agent_id}")
            return
        
        query = f"UPDATE conversations SET {column} = ? WHERE conversation_id = ?"
        self.db.execute(query, [chosen_name, conversation_id])
        
        logger.debug(f"Set {agent_id} name to '{chosen_name}' for conversation {conversation_id}")
    
    def get_agent_names(self, conversation_id: str) -> Dict[str, str]:
        """Get agent names for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict mapping agent_id to chosen name
        """
        result = self.db.execute(
            "SELECT agent_a_chosen_name, agent_b_chosen_name FROM conversations WHERE conversation_id = ?",
            [conversation_id]
        ).fetchone()
        
        if result:
            return {
                "agent_a": result[0] or "Agent A",
                "agent_b": result[1] or "Agent B"
            }
        
        return {"agent_a": "Agent A", "agent_b": "Agent B"}
    
    # Message Operations
    def save_message(self, conversation_id: str, turn_number: int, agent_id: str,
                    role: str, content: str, tokens_used: Optional[int] = None):
        """Save a message.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            role: Message role
            content: Message content
            tokens_used: Optional token count
        """
        query = """
            INSERT INTO messages (
                conversation_id, turn_number, agent_id,
                content, timestamp, token_count
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute(query, [
            conversation_id,
            turn_number,
            agent_id,
            content,
            datetime.now(),
            tokens_used or 0
        ])
        
        logger.debug(f"Saved message for {agent_id} in turn {turn_number} of conversation {conversation_id}")
    
    def get_turn_messages(self, conversation_id: str, turn_number: int) -> List[Dict[str, Any]]:
        """Get all messages for a turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            
        Returns:
            List of message dicts
        """
        query = """
            SELECT * FROM messages 
            WHERE conversation_id = ? AND turn_number = ?
            ORDER BY agent_id
        """
        
        results = self.db.execute(query, [conversation_id, turn_number]).fetchall()
        
        if not results:
            return []
        
        cols = [desc[0] for desc in self.db.description]
        return [dict(zip(cols, row)) for row in results]
    
    # Metrics Operations
    def log_turn_metrics(self, conversation_id: str, turn_number: int, metrics: Dict[str, Any]):
        """Log metrics for a turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            metrics: Dict of metric values
        """
        # Check if turn_metrics row exists
        existing = self.db.execute(
            "SELECT COUNT(*) FROM turn_metrics WHERE conversation_id = ? AND turn_number = ?",
            [conversation_id, turn_number]
        ).fetchone()[0]
        
        if existing > 0:
            # Update existing row
            set_clauses = []
            params = []
            for key, value in metrics.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
            query = f"""
                UPDATE turn_metrics 
                SET {', '.join(set_clauses)}
                WHERE conversation_id = ? AND turn_number = ?
            """
            params.extend([conversation_id, turn_number])
        else:
            # Insert new row
            query = """
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score, vocabulary_overlap, structural_similarity,
                    topic_similarity, style_match
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = [
                conversation_id,
                turn_number,
                datetime.now(),
                metrics.get("convergence_score", 0.0),
                metrics.get("vocabulary_overlap"),
                metrics.get("structural_similarity"),
                metrics.get("topic_similarity"),
                metrics.get("style_match")
            ]
        
        self.db.execute(query, params)
        logger.debug(f"Logged metrics for turn {turn_number} of conversation {conversation_id}")
    
    def log_message_metrics(self, conversation_id: str, turn_number: int, agent_id: str,
                           message_length: int, vocabulary_size: int, 
                           punctuation_ratio: float, sentiment_score: Optional[float] = None):
        """Log metrics for a message.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            message_length: Message length in characters
            vocabulary_size: Unique word count
            punctuation_ratio: Ratio of punctuation
            sentiment_score: Optional sentiment score
        """
        # Determine which columns to update based on agent_id
        if agent_id == "agent_a":
            length_col = "message_a_length"
            vocab_col = "message_a_unique_words"
        elif agent_id == "agent_b":
            length_col = "message_b_length"
            vocab_col = "message_b_unique_words"
        else:
            logger.warning(f"Unknown agent_id: {agent_id}")
            return
        
        # Ensure turn_metrics row exists
        existing = self.db.execute(
            "SELECT COUNT(*) FROM turn_metrics WHERE conversation_id = ? AND turn_number = ?",
            [conversation_id, turn_number]
        ).fetchone()[0]
        
        if existing == 0:
            # Create the row first
            self.log_turn_metrics(conversation_id, turn_number, {})
        
        # Update with message metrics
        query = f"""
            UPDATE turn_metrics 
            SET {length_col} = ?, {vocab_col} = ?
            WHERE conversation_id = ? AND turn_number = ?
        """
        
        self.db.execute(query, [
            message_length,
            vocabulary_size,
            conversation_id,
            turn_number
        ])
    
    def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregate metrics for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Dict of experiment metrics
        """
        # Get conversation stats
        conv_stats = self.db.execute("""
            SELECT 
                COUNT(*) as total_conversations,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                AVG(final_convergence_score) as avg_convergence,
                MAX(final_convergence_score) as max_convergence,
                MIN(final_convergence_score) as min_convergence
            FROM conversations
            WHERE experiment_id = ?
        """, [experiment_id]).fetchone()
        
        metrics = {
            "total_conversations": conv_stats[0] or 0,
            "completed_conversations": conv_stats[1] or 0,
            "failed_conversations": conv_stats[2] or 0,
            "avg_convergence": conv_stats[3] or 0.0,
            "max_convergence": conv_stats[4] or 0.0,
            "min_convergence": conv_stats[5] or 0.0
        }
        
        # Get turn stats
        turn_stats = self.db.execute("""
            SELECT 
                AVG(tm.convergence_score) as avg_turn_convergence,
                COUNT(DISTINCT tm.conversation_id) as conversations_with_metrics
            FROM turn_metrics tm
            JOIN conversations c ON tm.conversation_id = c.conversation_id
            WHERE c.experiment_id = ?
        """, [experiment_id]).fetchone()
        
        if turn_stats:
            metrics["avg_turn_convergence"] = turn_stats[0] or 0.0
            metrics["conversations_with_metrics"] = turn_stats[1] or 0
        
        return metrics
    
    def calculate_convergence_metrics(self, conversation_id: str) -> Dict[str, float]:
        """Calculate convergence metrics for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict with convergence metrics
        """
        # Get all turn metrics
        results = self.db.execute("""
            SELECT turn_number, convergence_score 
            FROM turn_metrics 
            WHERE conversation_id = ? 
            ORDER BY turn_number
        """, [conversation_id]).fetchall()
        
        if not results:
            return {
                "final_score": 0.0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "score_variance": 0.0
            }
        
        scores = [row[1] for row in results if row[1] is not None]
        
        if not scores:
            return {
                "final_score": 0.0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "score_variance": 0.0
            }
        
        import statistics
        
        return {
            "final_score": scores[-1],
            "average_score": statistics.mean(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "score_variance": statistics.variance(scores) if len(scores) > 1 else 0.0
        }
    
    # Token Usage Operations
    def log_token_usage(self, conversation_id: str, provider: str, model: str,
                       prompt_tokens: int, completion_tokens: int, total_cost: float):
        """Log token usage for billing/tracking.
        
        Args:
            conversation_id: Conversation ID
            provider: Provider name
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_cost: Total cost in dollars
        """
        query = """
            INSERT INTO token_usage (
                timestamp, conversation_id, provider, model,
                prompt_tokens, completion_tokens, total_tokens, total_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute(query, [
            datetime.now(),
            conversation_id,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            prompt_tokens + completion_tokens,
            total_cost
        ])
    
    # Deletion Operations
    def delete_experiment(self, experiment_id: str):
        """Delete an experiment and all related data.
        
        Args:
            experiment_id: Experiment ID to delete
        """
        # Use the existing _delete_experiment_data method
        self._delete_experiment_data(experiment_id)
        logger.info(f"Deleted experiment {experiment_id}")
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and related data.
        
        Args:
            conversation_id: Conversation ID to delete
        """
        # Delete in reverse dependency order
        tables = [
            "token_usage",
            "turn_metrics", 
            "messages",
            "events",
            "conversations"
        ]
        
        for table in tables:
            self.db.execute(f"DELETE FROM {table} WHERE conversation_id = ?", [conversation_id])
        
        logger.info(f"Deleted conversation {conversation_id}")
    
    # Backward Compatibility Methods
    def get_conversation_agent_configs(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get agent configurations from conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict with agent_a and agent_b configs or None
        """
        conv = self.get_conversation(conversation_id)
        if not conv:
            return None
        
        return {
            "agent_a": {
                "model": conv.get("agent_a_model", "unknown"),
                "temperature": conv.get("agent_a_temperature", 0.7)
            },
            "agent_b": {
                "model": conv.get("agent_b_model", "unknown"), 
                "temperature": conv.get("agent_b_temperature", 0.7)
            }
        }
    
    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get summary statistics for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Dict with experiment summary
        """
        exp = self.get_experiment(experiment_id)
        if not exp:
            return {}
        
        # Get conversation stats
        conversations = self.db.execute("""
            SELECT conversation_id, status 
            FROM conversations 
            WHERE experiment_id = ?
        """, [experiment_id]).fetchall()
        
        completed = sum(1 for c in conversations if c[1] == "completed")
        failed = sum(1 for c in conversations if c[1] == "failed")
        running = sum(1 for c in conversations if c[1] == "running")
        
        # Get metrics
        metrics = self.get_experiment_metrics(experiment_id)
        
        return {
            "experiment_id": experiment_id,
            "status": exp["status"],
            "total_conversations": len(conversations),
            "completed": completed,
            "failed": failed,
            "running": running,
            "started_at": exp.get("started_at"),
            "ended_at": exp.get("completed_at"),
            **metrics
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # JSONL Import functionality (replacing BatchImporter)
    def import_experiment_from_jsonl(self, exp_dir: Path, force: bool = False) -> ImportResult:
        """Import experiment data from JSONL files into database.
        
        Args:
            exp_dir: Directory containing manifest.json and JSONL files
            force: Force reimport even if already imported
            
        Returns:
            ImportResult with success status and counts
        """
        start_time = datetime.now()
        
        try:
            # Check for manifest
            manifest_path = exp_dir / "manifest.json"
            if not manifest_path.exists():
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="No manifest.json found"
                )
            
            # Check import status markers
            imported_marker = exp_dir / ".imported"
            importing_marker = exp_dir / ".importing"
            
            if imported_marker.exists() and not force:
                logger.info(f"Experiment {exp_dir.name} already imported")
                return ImportResult(
                    success=True,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="Already imported"
                )
            
            # Check if another import is in progress
            if importing_marker.exists():
                logger.warning(f"Import already in progress for {exp_dir.name}")
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="Import in progress"
                )
            
            # Mark as importing
            importing_marker.touch()
            
            try:
                # Load manifest
                with open(manifest_path) as f:
                    manifest_data = json.load(f)
                
                experiment_id = manifest_data.get("experiment_id", exp_dir.name)
                
                # If force flag is set, delete existing data BEFORE starting transaction
                if force:
                    logger.info(f"Force flag set - deleting existing data for {experiment_id}")
                    self._delete_experiment_data(experiment_id)
                    # Commit the deletes
                    self.db.commit()
                
                # Begin transaction for the import
                self.db.begin()
                
                # Import experiment record
                self._import_experiment_record(manifest_data)
                
                # Import conversations and events
                events_count = 0
                conversations_count = 0
                
                for conv_id, conv_info in manifest_data.get("conversations", {}).items():
                    jsonl_path = exp_dir / conv_info["jsonl"]
                    if jsonl_path.exists():
                        event_count = self._import_conversation_from_jsonl(
                            experiment_id, conv_id, jsonl_path
                        )
                        events_count += event_count
                        conversations_count += 1
                
                # Commit transaction
                self.db.commit()
                
                # Create imported marker
                importing_marker.unlink()
                with open(imported_marker, 'w') as f:
                    json.dump({
                        "imported_at": datetime.now().isoformat(),
                        "events_count": events_count,
                        "conversations_count": conversations_count
                    }, f)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"Successfully imported {experiment_id}: "
                          f"{events_count} events, {conversations_count} conversations")
                
                return ImportResult(
                    success=True,
                    experiment_id=experiment_id,
                    events_imported=events_count,
                    conversations_imported=conversations_count,
                    duration_seconds=duration
                )
                
            except Exception as e:
                # Rollback on error
                self.db.rollback()
                
                # Clean up importing marker
                if importing_marker.exists():
                    importing_marker.unlink()
                raise
                
        except Exception as e:
            logger.error(f"Failed to import {exp_dir.name}: {e}")
            
            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _import_experiment_record(self, manifest: Dict[str, Any]) -> None:
        """Import experiment metadata from manifest."""
        # Check if experiment already exists
        result = self.db.execute(
            "SELECT COUNT(*) FROM experiments WHERE experiment_id = ?",
            [manifest["experiment_id"]]
        ).fetchone()
        
        if result[0] > 0:
            # Update existing record
            self.db.execute("""
                UPDATE experiments SET
                    status = ?,
                    completed_conversations = ?,
                    failed_conversations = ?,
                    metadata = ?
                WHERE experiment_id = ?
            """, [
                manifest.get("status", "unknown"),
                manifest.get("completed_conversations", 0),
                manifest.get("failed_conversations", 0),
                json.dumps({
                    "manifest_version": "2.0",
                    "imported_at": datetime.now().isoformat()
                }),
                manifest["experiment_id"]
            ])
        else:
            # Insert new record
            self.db.execute("""
                INSERT INTO experiments (
                    experiment_id, name, created_at, started_at, completed_at,
                    status, config, total_conversations, 
                    completed_conversations, failed_conversations, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                manifest["experiment_id"],
                manifest.get("name") or manifest["experiment_id"],
                manifest.get("created_at"),
                manifest.get("started_at"),
                manifest.get("completed_at"),
                manifest.get("status", "unknown"),
                json.dumps(manifest.get("config", {})),
                manifest.get("total_conversations", 0),
                manifest.get("completed_conversations", 0),
                manifest.get("failed_conversations", 0),
                json.dumps({
                    "manifest_version": "2.0",
                    "imported_at": datetime.now().isoformat()
                })
            ])
    
    def _import_conversation_from_jsonl(self, experiment_id: str, 
                                       conversation_id: str,
                                       jsonl_path: Path) -> int:
        """Import a single conversation from JSONL file.
        
        Returns:
            Number of events imported
        """
        events_imported = 0
        conversation_data = {}
        pending_messages = []  # Store messages until conversation is created
        pending_metrics = []   # Store metrics until conversation is created
        token_counts = {}      # Map (agent_id, turn_num) -> token_count
        
        # First pass: Read JSONL and collect data
        with open(jsonl_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line.strip())
                    
                    # Insert event into events table
                    self.db.execute("""
                        INSERT INTO events (
                            timestamp, event_type, conversation_id, 
                            experiment_id, event_data, sequence
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        event.get("timestamp"),
                        event.get("event_type"),
                        conversation_id,
                        experiment_id,
                        json.dumps(event),
                        line_num
                    ])
                    events_imported += 1
                    
                    # Process specific event types for structured data
                    event_type = event.get("event_type")
                    
                    if event_type == "ConversationStartEvent":
                        # Extract conversation metadata
                        conversation_data.update({
                            "agent_a_model": event.get("agent_a_model"),
                            "agent_b_model": event.get("agent_b_model"),
                            "max_turns": event.get("max_turns"),
                            "initial_prompt": event.get("initial_prompt"),
                            "started_at": event.get("timestamp")
                        })
                    
                    elif event_type == "MessageCompleteEvent":
                        # Store token count for this agent (will be used in TurnCompleteEvent)
                        agent_id = event.get("agent_id")
                        tokens_used = event.get("tokens_used", 0)
                        # Find the turn number from recent message request events
                        # For now, store by agent_id and use latest when processing turn
                        token_counts[agent_id] = tokens_used
                    
                    elif event_type == "TurnCompleteEvent":
                        turn_num = event.get("turn_number", 0)
                        turn = event.get("turn", {})
                        
                        # Extract messages from turn data (this is the complete turn)
                        msg_a = turn.get("agent_a_message", {})
                        msg_b = turn.get("agent_b_message", {})
                        
                        # Store messages for this turn
                        if msg_a.get("content"):
                            pending_messages.append({
                                "conversation_id": conversation_id,
                                "turn_number": turn_num,
                                "agent_id": "agent_a",
                                "content": msg_a.get("content", ""),
                                "timestamp": msg_a.get("timestamp"),
                                "token_count": token_counts.get("agent_a", 0)
                            })
                        
                        if msg_b.get("content"):
                            pending_messages.append({
                                "conversation_id": conversation_id,
                                "turn_number": turn_num,
                                "agent_id": "agent_b", 
                                "content": msg_b.get("content", ""),
                                "timestamp": msg_b.get("timestamp"),
                                "token_count": token_counts.get("agent_b", 0)
                            })
                        
                        # Store turn metrics for later insertion
                        pending_metrics.append({
                            "conversation_id": conversation_id,
                            "turn_number": turn_num,
                            "timestamp": event.get("timestamp"),
                            "convergence_score": event.get("convergence_score", 0.0)
                        })
                        
                        # Update conversation data
                        conversation_data["final_convergence_score"] = event.get("convergence_score")
                        conversation_data["total_turns"] = turn_num
                    
                    elif event_type == "ConversationEndEvent":
                        conversation_data.update({
                            "status": "completed",
                            "completed_at": event.get("timestamp"),
                            "total_turns": event.get("total_turns", 0),
                            "convergence_reason": event.get("reason")
                        })
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line {line_num} in {jsonl_path}: {e}")
                    continue
        
        # Create conversation record first (to satisfy foreign key constraints)
        if conversation_data:
            # Check if conversation already exists
            result = self.db.execute(
                "SELECT COUNT(*) FROM conversations WHERE conversation_id = ?",
                [conversation_id]
            ).fetchone()
            
            if result[0] > 0:
                # Update existing
                self.db.execute("""
                    UPDATE conversations SET
                        status = ?,
                        completed_at = ?,
                        total_turns = ?,
                        final_convergence_score = ?
                    WHERE conversation_id = ?
                """, [
                    conversation_data.get("status", "unknown"),
                    conversation_data.get("completed_at"),
                    conversation_data.get("total_turns", 0),
                    conversation_data.get("final_convergence_score"),
                    conversation_id
                ])
            else:
                # Insert new conversation
                self.db.execute("""
                    INSERT INTO conversations (
                        conversation_id, experiment_id, started_at, completed_at,
                        status, agent_a_model, agent_b_model, max_turns, 
                        total_turns, initial_prompt, final_convergence_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    conversation_id,
                    experiment_id,
                    conversation_data.get("started_at"),
                    conversation_data.get("completed_at"),
                    conversation_data.get("status", "unknown"),
                    conversation_data.get("agent_a_model"),
                    conversation_data.get("agent_b_model"),
                    conversation_data.get("max_turns"),
                    conversation_data.get("total_turns", 0),
                    conversation_data.get("initial_prompt"),
                    conversation_data.get("final_convergence_score")
                ])
        
        # Now insert messages (conversation exists, turn numbers are correct)
        for msg in pending_messages:
            self.db.execute("""
                INSERT INTO messages (
                    conversation_id, turn_number, agent_id, 
                    content, timestamp, token_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                msg["conversation_id"],
                msg["turn_number"],
                msg["agent_id"],
                msg["content"],
                msg["timestamp"],
                msg["token_count"]
            ])
        
        # Insert turn metrics (conversation exists)
        for metric in pending_metrics:
            self.db.execute("""
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score
                ) VALUES (?, ?, ?, ?)
            """, [
                metric["conversation_id"],
                metric["turn_number"],
                metric["timestamp"],
                metric["convergence_score"]
            ])
        
        return events_imported
    
    def import_all_pending(self, experiments_dir: Path) -> List[ImportResult]:
        """Import all experiments that have JSONL files but haven't been imported.
        
        Args:
            experiments_dir: Root directory containing experiment subdirectories
            
        Returns:
            List of ImportResults for each experiment
        """
        results = []
        
        if not experiments_dir.exists():
            logger.warning(f"Experiments directory {experiments_dir} does not exist")
            return results
        
        # Find all experiment directories
        for exp_dir in experiments_dir.iterdir():
            if not exp_dir.is_dir() or exp_dir.name.startswith('.'):
                continue
            
            # Check if it has a manifest
            if not (exp_dir / "manifest.json").exists():
                continue
            
            # Import if not already imported
            result = self.import_experiment_from_jsonl(exp_dir)
            results.append(result)
        
        return results
    
    def _delete_experiment_data(self, experiment_id: str) -> None:
        """Delete all data for an experiment to allow clean reimport.
        
        Args:
            experiment_id: Experiment ID to delete
        """
        # Delete in reverse dependency order
        # First get all conversation IDs for this experiment
        result = self.db.execute(
            "SELECT conversation_id FROM conversations WHERE experiment_id = ?",
            [experiment_id]
        ).fetchall()
        
        conversation_ids = [row[0] for row in result]
        
        # Delete in reverse order of foreign key dependencies
        for conv_id in conversation_ids:
            # 1. Delete token usage (no dependencies)
            self.db.execute(
                "DELETE FROM token_usage WHERE conversation_id = ?",
                [conv_id]
            )
            
            # 2. Delete turn metrics (depends on conversations)
            self.db.execute(
                "DELETE FROM turn_metrics WHERE conversation_id = ?",
                [conv_id]
            )
            
            # 3. Delete messages (depends on conversations)
            self.db.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                [conv_id]
            )
        
        # 4. Delete conversations (depends on experiments)
        self.db.execute(
            "DELETE FROM conversations WHERE experiment_id = ?",
            [experiment_id]
        )
        
        # 5. Delete events (can reference both conversations and experiments)
        self.db.execute(
            "DELETE FROM events WHERE experiment_id = ?",
            [experiment_id]
        )
        
        # 6. Finally delete experiment
        self.db.execute(
            "DELETE FROM experiments WHERE experiment_id = ?",
            [experiment_id]
        )
        
        logger.info(f"Deleted all data for experiment {experiment_id}")
        logger.info(f"Deleted {len(conversation_ids)} conversations")