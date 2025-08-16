"""Repository for conversation operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.constants import ConversationStatus
from ..io.logger import get_logger
from .base_repository import BaseRepository

logger = get_logger("conversation_repository")


class ConversationRepository(BaseRepository):
    """Repository for conversation management operations."""

    def create_conversation(
        self, experiment_id: str, conversation_id: str, config: dict
    ):
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

        self.execute(
            query,
            [
                conversation_id,
                experiment_id,
                ConversationStatus.CREATED,
                datetime.now(),
                agent_a_config.get("model", "unknown"),
                agent_a_config.get("provider", "unknown"),
                agent_a_config.get("temperature", 0.7),
                agent_b_config.get("model", "unknown"),
                agent_b_config.get("provider", "unknown"),
                agent_b_config.get("temperature", 0.7),
                config.get("max_turns", 25),
                config.get("initial_prompt", ""),
            ],
        )

        logger.debug(
            f"Created conversation {conversation_id} for experiment {experiment_id}"
        )

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data as dict or None
        """
        result = self.fetchone(
            "SELECT * FROM conversations WHERE conversation_id = ?", [conversation_id]
        )

        if result:
            return self.row_to_dict(result)

        return None

    def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
        end_reason: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Update conversation status.

        Args:
            conversation_id: Conversation ID
            status: New status
            end_reason: Optional end reason
            error_message: Optional error message
        """
        if (
            status == ConversationStatus.COMPLETED
            or status == ConversationStatus.FAILED
        ):
            # Calculate final metrics if completing
            final_score = None
            total_turns = 0
            if status == ConversationStatus.COMPLETED:
                # Get the final convergence score from turn metrics
                result = self.fetchone(
                    """
                    SELECT turn_number, convergence_score
                    FROM turn_metrics
                    WHERE conversation_id = ?
                    ORDER BY turn_number DESC
                    LIMIT 1
                """,
                    [conversation_id],
                )

                if result:
                    total_turns = result[0]
                    final_score = result[1]

            query = """
                UPDATE conversations
                SET status = ?, completed_at = ?, convergence_reason = ?,
                    error_message = ?, final_convergence_score = ?, total_turns = ?
                WHERE conversation_id = ?
            """
            params = [
                status,
                datetime.now(),
                end_reason,
                error_message,
                final_score,
                total_turns,
                conversation_id,
            ]
        else:
            query = "UPDATE conversations SET status = ? WHERE conversation_id = ?"
            params = [status, conversation_id]

        self.execute(query, params)
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

        results = self.fetchall(query, [conversation_id])

        if not results:
            return []

        return [self.row_to_dict(row) for row in results]

    def log_agent_name(
        self,
        conversation_id: str,
        agent_id: str,
        chosen_name: str,
        turn_number: int = 0,
    ):
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
        self.execute(query, [chosen_name, conversation_id])

        logger.debug(
            f"Set {agent_id} name to '{chosen_name}' for conversation {conversation_id}"
        )

    def get_agent_names(self, conversation_id: str) -> Dict[str, str]:
        """Get agent names for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict mapping agent_id to chosen name
        """
        result = self.fetchone(
            "SELECT agent_a_chosen_name, agent_b_chosen_name FROM conversations WHERE conversation_id = ?",
            [conversation_id],
        )

        if result:
            return {
                "agent_a": result[0] or "Agent A",
                "agent_b": result[1] or "Agent B",
            }

        return {"agent_a": "Agent A", "agent_b": "Agent B"}

    def get_conversation_agent_configs(
        self, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get agent configurations from conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict with agent_a and agent_b configs or None
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        return {
            "agent_a": {
                "model": conversation.get("agent_a_model", "unknown"),
                "temperature": conversation.get("agent_a_temperature", 0.7),
            },
            "agent_b": {
                "model": conversation.get("agent_b_model", "unknown"),
                "temperature": conversation.get("agent_b_temperature", 0.7),
            },
        }

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation record.

        Args:
            conversation_id: Conversation ID to delete
        """
        self.execute(
            "DELETE FROM conversations WHERE conversation_id = ?", [conversation_id]
        )
        logger.debug(f"Deleted conversation {conversation_id}")

    def calculate_convergence_metrics(self, conversation_id: str) -> Dict[str, float]:
        """Calculate convergence metrics for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict with convergence metrics
        """
        # Get all turn metrics
        results = self.fetchall(
            """
            SELECT turn_number, convergence_score
            FROM turn_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number
        """,
            [conversation_id],
        )

        if not results:
            return {
                "final_score": 0.0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "score_variance": 0.0,
            }

        scores = [row[1] for row in results if row[1] is not None]

        if not scores:
            return {
                "final_score": 0.0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "score_variance": 0.0,
            }

        import statistics

        return {
            "final_score": scores[-1],
            "average_score": statistics.mean(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "score_variance": statistics.variance(scores) if len(scores) > 1 else 0.0,
        }
