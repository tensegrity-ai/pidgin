"""Repository for metrics operations."""

from datetime import datetime
from typing import Dict, Any, List, Optional

from .base_repository import BaseRepository
from ..io.logger import get_logger

logger = get_logger("metrics_repository")


class MetricsRepository(BaseRepository):
    """Repository for turn and message metrics operations."""
    
    def log_turn_metrics(self, conversation_id: str, turn_number: int, metrics: Dict[str, Any]):
        """Log metrics for a turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            metrics: Dict of metric values
        """
        # Check if turn_metrics row exists
        existing = self.exists("turn_metrics", 
                             conversation_id=conversation_id,
                             turn_number=turn_number)
        
        if existing:
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
        
        self.execute(query, params)
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
        if not self.exists("turn_metrics", 
                          conversation_id=conversation_id,
                          turn_number=turn_number):
            # Create the row first
            self.log_turn_metrics(conversation_id, turn_number, {})
        
        # Update with message metrics
        query = f"""
            UPDATE turn_metrics 
            SET {length_col} = ?, {vocab_col} = ?
            WHERE conversation_id = ? AND turn_number = ?
        """
        
        self.execute(query, [
            message_length,
            vocabulary_size,
            conversation_id,
            turn_number
        ])
    
    def get_turn_metrics(self, conversation_id: str, turn_number: int) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            
        Returns:
            Dict of metrics or None
        """
        result = self.fetchone(
            "SELECT * FROM turn_metrics WHERE conversation_id = ? AND turn_number = ?",
            [conversation_id, turn_number]
        )
        
        if result:
            metrics_dict = self.row_to_dict(result)
            # Parse JSON fields if any
            for field in ['word_frequencies_a', 'word_frequencies_b', 
                         'shared_vocabulary', 'extended_metrics']:
                if field in metrics_dict:
                    metrics_dict[field] = self.parse_json_field(metrics_dict[field])
            return metrics_dict
        
        return None
    
    def get_conversation_metrics(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all metrics for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of metric dicts ordered by turn
        """
        results = self.fetchall(
            "SELECT * FROM turn_metrics WHERE conversation_id = ? ORDER BY turn_number",
            [conversation_id]
        )
        
        metrics = []
        for row in results:
            metrics_dict = self.row_to_dict(row)
            # Parse JSON fields if any
            for field in ['word_frequencies_a', 'word_frequencies_b', 
                         'shared_vocabulary', 'extended_metrics']:
                if field in metrics_dict:
                    metrics_dict[field] = self.parse_json_field(metrics_dict[field])
            metrics.append(metrics_dict)
        
        return metrics
    
    def get_convergence_progression(self, conversation_id: str) -> List[tuple]:
        """Get convergence score progression for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of (turn_number, convergence_score) tuples
        """
        return self.fetchall("""
            SELECT turn_number, convergence_score 
            FROM turn_metrics 
            WHERE conversation_id = ? 
            ORDER BY turn_number
        """, [conversation_id])
    
    def delete_metrics_for_conversation(self, conversation_id: str):
        """Delete all metrics for a conversation.
        
        Args:
            conversation_id: Conversation ID
        """
        self.execute("DELETE FROM turn_metrics WHERE conversation_id = ?", [conversation_id])
        logger.debug(f"Deleted metrics for conversation {conversation_id}")
    
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
        
        self.execute(query, [
            datetime.now(),
            conversation_id,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            prompt_tokens + completion_tokens,
            total_cost
        ])
        
    def get_token_usage_stats(self, conversation_id: Optional[str] = None,
                            provider: Optional[str] = None) -> Dict[str, Any]:
        """Get token usage statistics.
        
        Args:
            conversation_id: Optional filter by conversation
            provider: Optional filter by provider
            
        Returns:
            Dict with usage statistics
        """
        conditions = []
        params = []
        
        if conversation_id:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)
        
        if provider:
            conditions.append("provider = ?")
            params.append(provider)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        result = self.fetchone(f"""
            SELECT 
                COUNT(*) as request_count,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(total_cost) as total_cost
            FROM token_usage{where_clause}
        """, params)
        
        if result:
            return {
                "request_count": result[0] or 0,
                "total_prompt_tokens": result[1] or 0,
                "total_completion_tokens": result[2] or 0,
                "total_tokens": result[3] or 0,
                "total_cost": result[4] or 0.0
            }
        
        return {
            "request_count": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }