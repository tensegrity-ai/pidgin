"""Repository for message storage and retrieval."""

from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseRepository
from ...io.logger import get_logger

logger = get_logger("message_repository")


class MessageRepository(BaseRepository):
    """Handles message storage and retrieval operations."""
    
    async def save_message(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ):
        """Save a message to the database.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            role: Message role (user/assistant)
            content: Message content
            tokens_used: Total tokens used
            input_tokens: Input token count
            output_tokens: Output token count
        """
        query = """
            INSERT INTO messages (
                conversation_id, turn_number, agent_id, role,
                content, timestamp, tokens_used, input_tokens, output_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            conversation_id,
            turn_number,
            agent_id,
            role,
            content,
            datetime.now(),
            tokens_used,
            input_tokens,
            output_tokens
        )
        
        await self.execute_query(query, params)
        logger.debug(f"Saved message from {agent_id} in turn {turn_number}")
    
    async def get_message(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific message.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            
        Returns:
            Message data or None
        """
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ? AND turn_number = ? AND agent_id = ?
        """
        
        return await self.fetch_one(query, (conversation_id, turn_number, agent_id))
    
    async def get_turn_messages(
        self,
        conversation_id: str,
        turn_number: int
    ) -> List[Dict[str, Any]]:
        """Get all messages for a specific turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            
        Returns:
            List of messages in the turn
        """
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ? AND turn_number = ?
            ORDER BY timestamp
        """
        
        return await self.fetch_all(query, (conversation_id, turn_number))
    
    async def get_agent_messages(
        self,
        conversation_id: str,
        agent_id: str
    ) -> List[Dict[str, Any]]:
        """Get all messages from a specific agent.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID
            
        Returns:
            List of agent's messages
        """
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ? AND agent_id = ?
            ORDER BY turn_number, timestamp
        """
        
        return await self.fetch_all(query, (conversation_id, agent_id))
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of messages
        """
        if limit is not None:
            query = """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY turn_number, timestamp
                LIMIT ? OFFSET ?
            """
            params = (conversation_id, limit, offset or 0)
        else:
            query = """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY turn_number, timestamp
            """
            params = (conversation_id,)
        
        return await self.fetch_all(query, params)
    
    async def count_messages(self, conversation_id: str) -> int:
        """Count total messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Total message count
        """
        query = """
            SELECT COUNT(*) as count FROM messages
            WHERE conversation_id = ?
        """
        
        result = await self.fetch_one(query, (conversation_id,))
        return result["count"] if result else 0
    
    async def get_last_message(
        self,
        conversation_id: str,
        agent_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the last message in a conversation.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Optional filter by agent
            
        Returns:
            Last message or None
        """
        if agent_id:
            query = """
                SELECT * FROM messages
                WHERE conversation_id = ? AND agent_id = ?
                ORDER BY turn_number DESC, timestamp DESC
                LIMIT 1
            """
            params = (conversation_id, agent_id)
        else:
            query = """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY turn_number DESC, timestamp DESC
                LIMIT 1
            """
            params = (conversation_id,)
        
        return await self.fetch_one(query, params)
    
    async def update_message_tokens(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        input_tokens: int,
        output_tokens: int
    ):
        """Update token counts for a message.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            input_tokens: Input token count
            output_tokens: Output token count
        """
        query = """
            UPDATE messages
            SET input_tokens = ?, output_tokens = ?, 
                tokens_used = ?
            WHERE conversation_id = ? AND turn_number = ? AND agent_id = ?
        """
        
        total_tokens = input_tokens + output_tokens
        params = (
            input_tokens,
            output_tokens,
            total_tokens,
            conversation_id,
            turn_number,
            agent_id
        )
        
        await self.execute_query(query, params)
        logger.debug(f"Updated token counts for {agent_id} message in turn {turn_number}")
    
    async def search_messages(
        self,
        conversation_id: str,
        search_term: str,
        case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Search messages by content.
        
        Args:
            conversation_id: Conversation ID
            search_term: Term to search for
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            List of matching messages
        """
        if case_sensitive:
            query = """
                SELECT * FROM messages
                WHERE conversation_id = ? AND content LIKE ?
                ORDER BY turn_number, timestamp
            """
        else:
            query = """
                SELECT * FROM messages
                WHERE conversation_id = ? AND LOWER(content) LIKE LOWER(?)
                ORDER BY turn_number, timestamp
            """
        
        # Add wildcards for LIKE search
        search_pattern = f"%{search_term}%"
        
        return await self.fetch_all(query, (conversation_id, search_pattern))
    
    async def get_message_stats(
        self,
        conversation_id: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get message statistics.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Optional filter by agent
            
        Returns:
            Statistics dictionary
        """
        if agent_id:
            query = """
                SELECT 
                    COUNT(*) as total_messages,
                    AVG(LENGTH(content)) as avg_length,
                    MAX(LENGTH(content)) as max_length,
                    MIN(LENGTH(content)) as min_length,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used) as avg_tokens
                FROM messages
                WHERE conversation_id = ? AND agent_id = ?
            """
            params = (conversation_id, agent_id)
        else:
            query = """
                SELECT 
                    COUNT(*) as total_messages,
                    AVG(LENGTH(content)) as avg_length,
                    MAX(LENGTH(content)) as max_length,
                    MIN(LENGTH(content)) as min_length,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used) as avg_tokens
                FROM messages
                WHERE conversation_id = ?
            """
            params = (conversation_id,)
        
        result = await self.fetch_one(query, params)
        
        # Ensure numeric values
        if result:
            return {
                "total_messages": result.get("total_messages", 0) or 0,
                "avg_length": result.get("avg_length", 0) or 0,
                "max_length": result.get("max_length", 0) or 0,
                "min_length": result.get("min_length", 0) or 0,
                "total_tokens": result.get("total_tokens", 0) or 0,
                "avg_tokens": result.get("avg_tokens", 0) or 0
            }
        
        return {
            "total_messages": 0,
            "avg_length": 0,
            "max_length": 0,
            "min_length": 0,
            "total_tokens": 0,
            "avg_tokens": 0
        }
    
    async def get_turn_range_messages(
        self,
        conversation_id: str,
        start_turn: int,
        end_turn: int
    ) -> List[Dict[str, Any]]:
        """Get messages within a turn range.
        
        Args:
            conversation_id: Conversation ID
            start_turn: Starting turn number (inclusive)
            end_turn: Ending turn number (inclusive)
            
        Returns:
            List of messages in the range
        """
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ? AND turn_number BETWEEN ? AND ?
            ORDER BY turn_number, timestamp
        """
        
        return await self.fetch_all(query, (conversation_id, start_turn, end_turn))
    
    async def delete_messages(self, conversation_id: str):
        """Delete all messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
        """
        query = "DELETE FROM messages WHERE conversation_id = ?"
        
        await self.execute_query(query, (conversation_id,))
        logger.info(f"Deleted all messages for conversation {conversation_id}")