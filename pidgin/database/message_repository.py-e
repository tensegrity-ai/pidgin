"""Repository for message operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..io.logger import get_logger
from .base_repository import BaseRepository

logger = get_logger("message_repository")


class MessageRepository(BaseRepository):
    """Repository for message storage and retrieval operations."""

    def save_message(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
    ):
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

        self.execute(
            query,
            [
                conversation_id,
                turn_number,
                agent_id,
                content,
                datetime.now(),
                tokens_used or 0,
            ],
        )

        logger.debug(
            f"Saved message for {agent_id} in turn {turn_number} of conversation {conversation_id}"
        )

    def get_turn_messages(
        self, conversation_id: str, turn_number: int
    ) -> List[Dict[str, Any]]:
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

        results = self.fetchall(query, [conversation_id, turn_number])

        if not results:
            return []

        return [self.row_to_dict(row) for row in results]

    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation.

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

        results = self.fetchall(query, [conversation_id])

        if not results:
            return []

        return [self.row_to_dict(row) for row in results]

    def get_message_count(self, conversation_id: str) -> int:
        """Get total message count for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Number of messages
        """
        return self.count("messages", conversation_id=conversation_id)

    def get_total_tokens(self, conversation_id: str) -> int:
        """Get total token count for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Total tokens used
        """
        result = self.fetchone(
            "SELECT SUM(token_count) FROM messages WHERE conversation_id = ?",
            [conversation_id],
        )
        return result[0] if result and result[0] else 0

    def delete_messages_for_conversation(self, conversation_id: str):
        """Delete all messages for a conversation.

        Args:
            conversation_id: Conversation ID
        """
        self.execute(
            "DELETE FROM messages WHERE conversation_id = ?", [conversation_id]
        )
        logger.debug(f"Deleted messages for conversation {conversation_id}")

    def get_agent_message_stats(
        self, conversation_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """Get message statistics for an agent in a conversation.

        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID

        Returns:
            Dict with message stats
        """
        result = self.fetchone(
            """
            SELECT
                COUNT(*) as message_count,
                SUM(LENGTH(content)) as total_chars,
                AVG(LENGTH(content)) as avg_chars,
                SUM(token_count) as total_tokens,
                AVG(token_count) as avg_tokens
            FROM messages
            WHERE conversation_id = ? AND agent_id = ?
        """,
            [conversation_id, agent_id],
        )

        if result:
            return {
                "message_count": result[0] or 0,
                "total_chars": result[1] or 0,
                "avg_chars": result[2] or 0.0,
                "total_tokens": result[3] or 0,
                "avg_tokens": result[4] or 0.0,
            }

        return {
            "message_count": 0,
            "total_chars": 0,
            "avg_chars": 0.0,
            "total_tokens": 0,
            "avg_tokens": 0.0,
        }
