"""Repository for thinking trace operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..io.logger import get_logger
from .base_repository import BaseRepository

logger = get_logger("thinking_repository")


class ThinkingRepository(BaseRepository):
    """Repository for thinking trace storage and retrieval operations."""

    def save_thinking_trace(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        thinking_content: str,
        thinking_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Save a thinking trace.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            thinking_content: The thinking/reasoning content
            thinking_tokens: Optional token count for thinking
            duration_ms: Optional duration of thinking phase in milliseconds
            timestamp: Optional timestamp (defaults to now)
        """
        query = """
            INSERT INTO thinking_traces (
                conversation_id, turn_number, agent_id,
                thinking_content, thinking_tokens, duration_ms, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        self.execute(
            query,
            [
                conversation_id,
                turn_number,
                agent_id,
                thinking_content,
                thinking_tokens,
                duration_ms,
                timestamp or datetime.now(),
            ],
        )

        logger.debug(
            f"Saved thinking trace for {agent_id} in turn {turn_number} "
            f"({thinking_tokens or 'unknown'} tokens)"
        )

    def get_thinking_for_turn(
        self, conversation_id: str, turn_number: int, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get thinking trace for a specific turn and agent.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID

        Returns:
            Thinking trace dict or None
        """
        query = """
            SELECT * FROM thinking_traces
            WHERE conversation_id = ? AND turn_number = ? AND agent_id = ?
        """

        result = self.fetchone(query, [conversation_id, turn_number, agent_id])

        if not result:
            return None

        return self.row_to_dict(result)

    def get_thinking_for_conversation(
        self, conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Get all thinking traces for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of thinking trace dicts ordered by turn and agent
        """
        query = """
            SELECT * FROM thinking_traces
            WHERE conversation_id = ?
            ORDER BY turn_number, agent_id
        """

        results = self.fetchall(query, [conversation_id])

        if not results:
            return []

        return [self.row_to_dict(row) for row in results]

    def get_total_thinking_tokens(self, conversation_id: str) -> int:
        """Get total thinking token count for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Total thinking tokens used
        """
        result = self.fetchone(
            "SELECT SUM(thinking_tokens) FROM thinking_traces WHERE conversation_id = ?",
            [conversation_id],
        )
        return result[0] if result and result[0] else 0

    def get_agent_thinking_stats(
        self, conversation_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """Get thinking statistics for an agent in a conversation.

        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID

        Returns:
            Dict with thinking stats
        """
        result = self.fetchone(
            """
            SELECT
                COUNT(*) as trace_count,
                SUM(thinking_tokens) as total_tokens,
                AVG(thinking_tokens) as avg_tokens,
                SUM(duration_ms) as total_duration_ms,
                AVG(duration_ms) as avg_duration_ms
            FROM thinking_traces
            WHERE conversation_id = ? AND agent_id = ?
        """,
            [conversation_id, agent_id],
        )

        if result:
            return {
                "trace_count": result[0] or 0,
                "total_tokens": result[1] or 0,
                "avg_tokens": result[2] or 0.0,
                "total_duration_ms": result[3] or 0,
                "avg_duration_ms": result[4] or 0.0,
            }

        return {
            "trace_count": 0,
            "total_tokens": 0,
            "avg_tokens": 0.0,
            "total_duration_ms": 0,
            "avg_duration_ms": 0.0,
        }

    def delete_thinking_for_conversation(self, conversation_id: str):
        """Delete all thinking traces for a conversation.

        Args:
            conversation_id: Conversation ID
        """
        self.execute(
            "DELETE FROM thinking_traces WHERE conversation_id = ?", [conversation_id]
        )
        logger.debug(f"Deleted thinking traces for conversation {conversation_id}")
