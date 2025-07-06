"""Repository for experiment management."""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseRepository
from ...io.logger import get_logger

logger = get_logger("experiment_repository")


class ExperimentRepository(BaseRepository):
    """Handles experiment storage and management operations."""
    
    async def create_experiment(self, name: str, config: dict) -> str:
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
                created_at, total_conversations, completed_conversations
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            experiment_id,
            name,
            json.dumps(config),
            "created",
            created_at,
            0,  # total_conversations
            0   # completed_conversations
        )
        
        await self.execute_query(query, params)
        
        logger.info(f"Created experiment {experiment_id}: {name}")
        return experiment_id
    
    async def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment data or None if not found
        """
        query = """
            SELECT * FROM experiments 
            WHERE experiment_id = ?
        """
        
        result = await self.fetch_one(query, (experiment_id,))
        
        if result:
            # Parse JSON config
            if "config" in result and isinstance(result["config"], str):
                try:
                    result["config"] = json.loads(result["config"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse config for experiment {experiment_id}")
                    result["config"] = {}
        
        return result
    
    async def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get experiment by name.
        
        Args:
            name: Experiment name
            
        Returns:
            Experiment data or None if not found
        """
        query = """
            SELECT * FROM experiments 
            WHERE name = ?
        """
        
        result = await self.fetch_one(query, (name,))
        
        if result and "config" in result and isinstance(result["config"], str):
            try:
                result["config"] = json.loads(result["config"])
            except json.JSONDecodeError:
                result["config"] = {}
        
        return result
    
    async def update_experiment_status(
        self, 
        experiment_id: str, 
        status: str,
        error_message: Optional[str] = None
    ):
        """Update experiment status.
        
        Args:
            experiment_id: Experiment ID
            status: New status
            error_message: Optional error message for failed status
        """
        # First check if experiment exists
        check_query = "SELECT COUNT(*) as count FROM experiments WHERE experiment_id = ?"
        result = await self.fetch_one(check_query, (experiment_id,))
        
        if not result or result["count"] == 0:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Update status
        if error_message:
            query = """
                UPDATE experiments 
                SET status = ?, error_message = ?, updated_at = ?
                WHERE experiment_id = ?
            """
            params = (status, error_message, datetime.now(), experiment_id)
        else:
            query = """
                UPDATE experiments 
                SET status = ?, updated_at = ?
                WHERE experiment_id = ?
            """
            params = (status, datetime.now(), experiment_id)
        
        await self.execute_query(query, params)
        
        # If completed, set completed_at
        if status in ["completed", "failed"]:
            complete_query = """
                UPDATE experiments 
                SET completed_at = ?
                WHERE experiment_id = ?
            """
            await self.execute_query(complete_query, (datetime.now(), experiment_id))
    
    async def update_experiment_config(self, experiment_id: str, config: dict):
        """Update experiment configuration.
        
        Args:
            experiment_id: Experiment ID
            config: New configuration
        """
        query = """
            UPDATE experiments 
            SET config = ?, updated_at = ?
            WHERE experiment_id = ?
        """
        
        params = (json.dumps(config), datetime.now(), experiment_id)
        await self.execute_query(query, params)
    
    async def list_experiments(
        self, 
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List experiments with optional status filter.
        
        Args:
            status_filter: Filter by status
            
        Returns:
            List of experiments
        """
        if status_filter:
            query = """
                SELECT * FROM experiments 
                WHERE status = ?
                ORDER BY created_at DESC
            """
            params = (status_filter,)
        else:
            query = """
                SELECT * FROM experiments 
                ORDER BY created_at DESC
            """
            params = None
        
        results = await self.fetch_all(query, params)
        
        # Parse JSON configs
        for exp in results:
            if "config" in exp and isinstance(exp["config"], str):
                try:
                    exp["config"] = json.loads(exp["config"])
                except json.JSONDecodeError:
                    exp["config"] = {}
        
        return results
    
    async def mark_running_conversations_failed(self, experiment_id: str):
        """Mark all running conversations in an experiment as failed.
        
        Args:
            experiment_id: Experiment ID
        """
        query = """
            UPDATE conversations 
            SET status = ?, end_reason = ?, ended_at = ?
            WHERE experiment_id = ? AND status = 'running'
        """
        
        params = (
            "failed",
            "experiment_stopped",
            datetime.now(),
            experiment_id
        )
        
        await self.execute_query(query, params)
        
        logger.info(f"Marked running conversations as failed for experiment {experiment_id}")
    
    async def get_experiment_stats(self, experiment_id: str) -> Dict[str, Any]:
        """Get statistics for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Statistics dictionary
        """
        # Get conversation counts
        conv_query = """
            SELECT 
                COUNT(*) as total_conversations,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_conversations,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_conversations
            FROM conversations
            WHERE experiment_id = ?
        """
        
        conv_stats = await self.fetch_one(conv_query, (experiment_id,))
        
        # Get message and turn stats
        msg_query = """
            SELECT 
                COUNT(*) as total_messages,
                AVG(turn_count) as avg_turns_per_conversation
            FROM (
                SELECT 
                    c.conversation_id,
                    COUNT(DISTINCT m.turn_number) as turn_count
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE c.experiment_id = ?
                GROUP BY c.conversation_id
            ) t
        """
        
        msg_stats = await self.fetch_one(msg_query, (experiment_id,))
        
        # Get token usage
        token_query = """
            SELECT 
                SUM(total_tokens) as total_tokens
            FROM token_usage
            WHERE conversation_id IN (
                SELECT conversation_id 
                FROM conversations 
                WHERE experiment_id = ?
            )
        """
        
        token_stats = await self.fetch_one(token_query, (experiment_id,))
        
        # Combine stats
        stats = {
            "total_conversations": conv_stats.get("total_conversations", 0) if conv_stats else 0,
            "completed_conversations": conv_stats.get("completed_conversations", 0) if conv_stats else 0,
            "failed_conversations": conv_stats.get("failed_conversations", 0) if conv_stats else 0,
            "total_messages": msg_stats.get("total_messages", 0) if msg_stats else 0,
            "avg_turns_per_conversation": msg_stats.get("avg_turns_per_conversation", 0) if msg_stats else 0,
            "total_tokens": token_stats.get("total_tokens", 0) if token_stats else 0
        }
        
        return stats
    
    async def delete_experiment(self, experiment_id: str):
        """Delete an experiment and all related data.
        
        Args:
            experiment_id: Experiment ID
        """
        # Delete in order to respect foreign key constraints
        # 1. Delete events
        await self.execute_query(
            "DELETE FROM events WHERE experiment_id = ?",
            (experiment_id,)
        )
        
        # 2. Delete token usage
        await self.execute_query(
            """DELETE FROM token_usage WHERE conversation_id IN 
               (SELECT conversation_id FROM conversations WHERE experiment_id = ?)""",
            (experiment_id,)
        )
        
        # 3. Delete messages
        await self.execute_query(
            """DELETE FROM messages WHERE conversation_id IN 
               (SELECT conversation_id FROM conversations WHERE experiment_id = ?)""",
            (experiment_id,)
        )
        
        # 4. Delete conversations
        await self.execute_query(
            "DELETE FROM conversations WHERE experiment_id = ?",
            (experiment_id,)
        )
        
        # 5. Delete experiment
        await self.execute_query(
            "DELETE FROM experiments WHERE experiment_id = ?",
            (experiment_id,)
        )
        
        logger.info(f"Deleted experiment {experiment_id} and all related data")