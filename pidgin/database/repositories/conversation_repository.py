"""Repository for conversation management."""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseRepository
from ...io.logger import get_logger

logger = get_logger("conversation_repository")


class ConversationRepository(BaseRepository):
    """Handles conversation storage and management operations."""
    
    async def create_conversation(
        self,
        experiment_id: str,
        conversation_id: str,
        config: dict
    ):
        """Create a new conversation.
        
        Args:
            experiment_id: Parent experiment ID
            conversation_id: Unique conversation ID
            config: Conversation configuration
        """
        query = """
            INSERT INTO conversations (
                conversation_id, experiment_id, config, status,
                started_at, total_messages, total_turns
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            conversation_id,
            experiment_id,
            json.dumps(config),
            "created",
            datetime.now(),
            0,  # total_messages
            0   # total_turns
        )
        
        await self.execute_query(query, params)
        logger.info(f"Created conversation {conversation_id} for experiment {experiment_id}")
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation data or None if not found
        """
        query = """
            SELECT * FROM conversations
            WHERE conversation_id = ?
        """
        
        result = await self.fetch_one(query, (conversation_id,))
        
        if result:
            # Parse JSON config
            if "config" in result and isinstance(result["config"], str):
                try:
                    result["config"] = json.loads(result["config"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse config for conversation {conversation_id}")
                    result["config"] = {}
        
        return result
    
    async def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
        end_reason: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update conversation status.
        
        Args:
            conversation_id: Conversation ID
            status: New status
            end_reason: Optional reason for ending
            error_message: Optional error message
        """
        # Check if conversation exists
        check_query = "SELECT COUNT(*) as count FROM conversations WHERE conversation_id = ?"
        result = await self.fetch_one(check_query, (conversation_id,))
        
        if not result or result["count"] == 0:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Build update query
        if error_message:
            query = """
                UPDATE conversations 
                SET status = ?, end_reason = ?, error_message = ?, updated_at = ?
                WHERE conversation_id = ?
            """
            params = (status, end_reason, error_message, datetime.now(), conversation_id)
        else:
            query = """
                UPDATE conversations 
                SET status = ?, end_reason = ?, updated_at = ?
                WHERE conversation_id = ?
            """
            params = (status, end_reason, datetime.now(), conversation_id)
        
        await self.execute_query(query, params)
        
        # If ending, set ended_at
        if status in ["completed", "failed"]:
            end_query = """
                UPDATE conversations 
                SET ended_at = ?
                WHERE conversation_id = ?
            """
            await self.execute_query(end_query, (datetime.now(), conversation_id))
        
        logger.info(f"Updated conversation {conversation_id} status to {status}")
    
    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get message history for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of messages ordered by turn and timestamp
        """
        query = """
            SELECT turn_number, agent_id, role, content, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY turn_number, timestamp
        """
        
        messages = await self.fetch_all(query, (conversation_id,))
        return messages
    
    async def log_agent_name(
        self,
        conversation_id: str,
        agent_id: str,
        chosen_name: str,
        turn_number: int = 0
    ):
        """Log agent's chosen name.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID (agent_a or agent_b)
            chosen_name: Name chosen by agent
            turn_number: Turn when name was chosen
        """
        query = """
            INSERT INTO agent_names (
                conversation_id, agent_id, chosen_name, turn_number
            ) VALUES (?, ?, ?, ?)
        """
        
        params = (conversation_id, agent_id, chosen_name, turn_number)
        await self.execute_query(query, params)
        
        logger.info(f"Agent {agent_id} chose name '{chosen_name}' in conversation {conversation_id}")
    
    async def get_agent_names(self, conversation_id: str) -> Dict[str, str]:
        """Get agent names for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dict mapping agent_id to chosen_name
        """
        query = """
            SELECT agent_id, chosen_name
            FROM agent_names
            WHERE conversation_id = ?
        """
        
        results = await self.fetch_all(query, (conversation_id,))
        
        # Convert to dict
        names = {}
        for row in results:
            names[row["agent_id"]] = row["chosen_name"]
        
        return names
    
    async def list_conversations_by_experiment(
        self,
        experiment_id: str,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List conversations for an experiment.
        
        Args:
            experiment_id: Experiment ID
            status_filter: Optional status filter
            
        Returns:
            List of conversations
        """
        if status_filter:
            query = """
                SELECT conversation_id, status, started_at, ended_at, 
                       total_turns, total_messages, end_reason
                FROM conversations
                WHERE experiment_id = ? AND status = ?
                ORDER BY started_at DESC
            """
            params = (experiment_id, status_filter)
        else:
            query = """
                SELECT conversation_id, status, started_at, ended_at,
                       total_turns, total_messages, end_reason
                FROM conversations
                WHERE experiment_id = ?
                ORDER BY started_at DESC
            """
            params = (experiment_id,)
        
        return await self.fetch_all(query, params)
    
    async def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get statistics for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Statistics dictionary
        """
        # Get basic stats
        conv_query = """
            SELECT 
                total_messages,
                total_turns,
                CASE 
                    WHEN ended_at IS NOT NULL AND started_at IS NOT NULL 
                    THEN (julianday(ended_at) - julianday(started_at)) * 86400
                    ELSE NULL
                END as duration_seconds
            FROM conversations
            WHERE conversation_id = ?
        """
        
        conv_stats = await self.fetch_one(conv_query, (conversation_id,))
        
        # Get message stats
        msg_query = """
            SELECT 
                COUNT(*) as message_count,
                AVG(LENGTH(content)) as avg_message_length,
                MAX(LENGTH(content)) as max_message_length,
                MIN(LENGTH(content)) as min_message_length
            FROM messages
            WHERE conversation_id = ?
        """
        
        msg_stats = await self.fetch_one(msg_query, (conversation_id,))
        
        # Get token stats
        token_query = """
            SELECT 
                SUM(total_tokens) as total_tokens,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens
            FROM token_usage
            WHERE conversation_id = ?
        """
        
        token_stats = await self.fetch_one(token_query, (conversation_id,))
        
        # Combine stats
        stats = {
            "total_messages": conv_stats.get("total_messages", 0) if conv_stats else 0,
            "total_turns": conv_stats.get("total_turns", 0) if conv_stats else 0,
            "duration_seconds": conv_stats.get("duration_seconds") if conv_stats else None,
            "avg_message_length": msg_stats.get("avg_message_length", 0) if msg_stats else 0,
            "max_message_length": msg_stats.get("max_message_length", 0) if msg_stats else 0,
            "min_message_length": msg_stats.get("min_message_length", 0) if msg_stats else 0,
            "total_tokens": token_stats.get("total_tokens", 0) if token_stats else 0
        }
        
        return stats
    
    async def update_conversation_metrics(
        self,
        conversation_id: str,
        total_messages: Optional[int] = None,
        total_turns: Optional[int] = None,
        total_tokens: Optional[int] = None
    ):
        """Update conversation metrics.
        
        Args:
            conversation_id: Conversation ID
            total_messages: Total message count
            total_turns: Total turn count
            total_tokens: Total token count
        """
        updates = []
        params = []
        
        if total_messages is not None:
            updates.append("total_messages = ?")
            params.append(total_messages)
        
        if total_turns is not None:
            updates.append("total_turns = ?")
            params.append(total_turns)
            
        if total_tokens is not None:
            updates.append("total_tokens = ?")
            params.append(total_tokens)
        
        if not updates:
            return
        
        query = f"""
            UPDATE conversations 
            SET {", ".join(updates)}, updated_at = ?
            WHERE conversation_id = ?
        """
        
        params.extend([datetime.now(), conversation_id])
        await self.execute_query(query, tuple(params))
    
    async def get_active_conversations(self) -> List[Dict[str, Any]]:
        """Get all currently active conversations.
        
        Returns:
            List of active conversations
        """
        query = """
            SELECT conversation_id, experiment_id, started_at,
                   total_turns, total_messages
            FROM conversations
            WHERE status = 'running'
            ORDER BY started_at DESC
        """
        
        return await self.fetch_all(query)
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all related data.
        
        Args:
            conversation_id: Conversation ID
        """
        # Delete in order to respect constraints
        # 1. Delete events
        await self.execute_query(
            "DELETE FROM events WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        # 2. Delete messages
        await self.execute_query(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        # 3. Delete token usage
        await self.execute_query(
            "DELETE FROM token_usage WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        # 4. Delete agent names
        await self.execute_query(
            "DELETE FROM agent_names WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        # 5. Delete metrics
        await self.execute_query(
            "DELETE FROM turn_metrics WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        # 6. Delete conversation
        await self.execute_query(
            "DELETE FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        logger.info(f"Deleted conversation {conversation_id} and all related data")