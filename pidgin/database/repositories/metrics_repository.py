"""Repository for metrics storage and analysis."""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseRepository
from ...io.logger import get_logger

logger = get_logger("metrics_repository")


class MetricsRepository(BaseRepository):
    """Handles metrics storage and retrieval operations."""
    
    async def log_turn_metrics(
        self,
        conversation_id: str,
        turn_number: int,
        metrics: Dict[str, Any]
    ):
        """Log metrics for a conversation turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            metrics: Dictionary of metric values
        """
        # Extract known metrics
        vocabulary_overlap = metrics.get("vocabulary_overlap")
        message_length_variance = metrics.get("message_length_variance")
        turn_taking_balance = metrics.get("turn_taking_balance")
        engagement_score = metrics.get("engagement_score")
        
        query = """
            INSERT INTO turn_metrics (
                conversation_id, turn_number, vocabulary_overlap,
                message_length_variance, turn_taking_balance,
                engagement_score, timestamp, additional_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Store any additional metrics as JSON
        known_metrics = {
            "vocabulary_overlap", "message_length_variance",
            "turn_taking_balance", "engagement_score"
        }
        additional = {k: v for k, v in metrics.items() if k not in known_metrics}
        
        params = (
            conversation_id,
            turn_number,
            vocabulary_overlap,
            message_length_variance,
            turn_taking_balance,
            engagement_score,
            datetime.now(),
            json.dumps(additional) if additional else None
        )
        
        await self.execute_query(query, params)
        logger.debug(f"Logged turn metrics for {conversation_id} turn {turn_number}")
    
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
        """Log metrics for a single message.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            message_length: Length of message in characters
            vocabulary_size: Number of unique words
            punctuation_ratio: Ratio of punctuation to total characters
            sentiment_score: Optional sentiment score
        """
        query = """
            INSERT INTO message_metrics (
                conversation_id, turn_number, agent_id,
                message_length, vocabulary_size, punctuation_ratio,
                sentiment_score, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            conversation_id,
            turn_number,
            agent_id,
            message_length,
            vocabulary_size,
            punctuation_ratio,
            sentiment_score,
            datetime.now()
        )
        
        await self.execute_query(query, params)
    
    async def log_word_frequencies(
        self,
        conversation_id: str,
        turn_number: int,
        agent_id: str,
        word_frequencies: Dict[str, int]
    ):
        """Log word frequency data.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            agent_id: Agent ID
            word_frequencies: Dict of word -> count
        """
        if not word_frequencies:
            return
        
        # Batch insert word frequencies
        query = """
            INSERT INTO word_frequencies (
                conversation_id, turn_number, agent_id,
                word, frequency
            ) VALUES (?, ?, ?, ?, ?)
        """
        
        # Prepare batch data
        batch_data = []
        for word, freq in word_frequencies.items():
            batch_data.append((
                conversation_id,
                turn_number,
                agent_id,
                word,
                freq
            ))
        
        # Execute batch insert
        for params in batch_data:
            await self.execute_query(query, params)
        
        logger.debug(f"Logged {len(word_frequencies)} word frequencies for {agent_id}")
    
    async def get_turn_metrics(
        self,
        conversation_id: str,
        turn_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific turn.
        
        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            
        Returns:
            Turn metrics or None
        """
        query = """
            SELECT * FROM turn_metrics
            WHERE conversation_id = ? AND turn_number = ?
        """
        
        result = await self.fetch_one(query, (conversation_id, turn_number))
        
        if result and "additional_metrics" in result and result["additional_metrics"]:
            try:
                additional = json.loads(result["additional_metrics"])
                result.update(additional)
            except json.JSONDecodeError:
                pass
        
        return result
    
    async def get_conversation_metrics(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Get all turn metrics for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of turn metrics ordered by turn number
        """
        query = """
            SELECT * FROM turn_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number
        """
        
        results = await self.fetch_all(query, (conversation_id,))
        
        # Parse additional metrics
        for result in results:
            if "additional_metrics" in result and result["additional_metrics"]:
                try:
                    additional = json.loads(result["additional_metrics"])
                    result.update(additional)
                except json.JSONDecodeError:
                    pass
        
        return results
    
    async def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for an entire experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Aggregated metrics dictionary
        """
        # Get turn-level aggregates
        turn_query = """
            SELECT 
                AVG(tm.vocabulary_overlap) as avg_vocabulary_overlap,
                AVG(tm.message_length_variance) as avg_message_length_variance,
                AVG(tm.turn_taking_balance) as avg_turn_taking_balance,
                AVG(tm.engagement_score) as avg_engagement,
                COUNT(DISTINCT tm.conversation_id) as total_conversations
            FROM turn_metrics tm
            JOIN conversations c ON tm.conversation_id = c.conversation_id
            WHERE c.experiment_id = ?
        """
        
        turn_stats = await self.fetch_one(turn_query, (experiment_id,))
        
        # Get message-level aggregates
        msg_query = """
            SELECT 
                AVG(mm.message_length) as avg_message_length,
                AVG(mm.vocabulary_size) as avg_vocabulary_size,
                AVG(mm.punctuation_ratio) as avg_punctuation_ratio,
                AVG(mm.sentiment_score) as avg_sentiment
            FROM message_metrics mm
            JOIN conversations c ON mm.conversation_id = c.conversation_id
            WHERE c.experiment_id = ?
        """
        
        msg_stats = await self.fetch_one(msg_query, (experiment_id,))
        
        # Get word statistics
        word_query = """
            SELECT 
                COUNT(DISTINCT wf.word) as total_unique_words,
                SUM(wf.frequency) as total_words,
                AVG(wf.frequency) as avg_word_frequency,
                COUNT(DISTINCT wf.word) * 1.0 / COUNT(DISTINCT wf.turn_number) as avg_words_per_turn
            FROM word_frequencies wf
            JOIN conversations c ON wf.conversation_id = c.conversation_id
            WHERE c.experiment_id = ?
        """
        
        word_stats = await self.fetch_one(word_query, (experiment_id,))
        
        # Combine all metrics
        metrics = {}
        
        if turn_stats:
            metrics.update({
                "avg_vocabulary_overlap": turn_stats.get("avg_vocabulary_overlap", 0),
                "avg_message_length_variance": turn_stats.get("avg_message_length_variance", 0),
                "avg_turn_taking_balance": turn_stats.get("avg_turn_taking_balance", 0),
                "avg_engagement": turn_stats.get("avg_engagement", 0),
                "total_conversations": turn_stats.get("total_conversations", 0)
            })
        
        if msg_stats:
            metrics.update({
                "avg_message_length": msg_stats.get("avg_message_length", 0),
                "avg_vocabulary_size": msg_stats.get("avg_vocabulary_size", 0),
                "avg_punctuation_ratio": msg_stats.get("avg_punctuation_ratio", 0),
                "avg_sentiment": msg_stats.get("avg_sentiment", 0)
            })
        
        if word_stats:
            metrics.update({
                "total_unique_words": word_stats.get("total_unique_words", 0),
                "total_words": word_stats.get("total_words", 0),
                "avg_word_frequency": word_stats.get("avg_word_frequency", 0),
                "avg_words_per_turn": word_stats.get("avg_words_per_turn", 0)
            })
        
        return metrics
    
    async def get_agent_metrics(
        self,
        conversation_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Get metrics for a specific agent in a conversation.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID
            
        Returns:
            Agent-specific metrics
        """
        # Get message metrics
        msg_query = """
            SELECT 
                COUNT(*) as total_messages,
                AVG(message_length) as avg_message_length,
                SUM(message_length) as total_characters,
                AVG(vocabulary_size) as avg_vocabulary_size,
                AVG(punctuation_ratio) as avg_punctuation_ratio,
                AVG(sentiment_score) as avg_sentiment
            FROM message_metrics
            WHERE conversation_id = ? AND agent_id = ?
        """
        
        msg_stats = await self.fetch_one(msg_query, (conversation_id, agent_id))
        
        # Get word statistics
        word_query = """
            SELECT 
                COUNT(DISTINCT word) as unique_words,
                SUM(frequency) as total_words,
                MAX(frequency) as most_frequent_word_count
            FROM word_frequencies
            WHERE conversation_id = ? AND agent_id = ?
        """
        
        word_stats = await self.fetch_one(word_query, (conversation_id, agent_id))
        
        # Combine metrics
        metrics = {
            "total_messages": msg_stats.get("total_messages", 0) if msg_stats else 0,
            "avg_message_length": msg_stats.get("avg_message_length", 0) if msg_stats else 0,
            "total_characters": msg_stats.get("total_characters", 0) if msg_stats else 0,
            "avg_vocabulary_size": msg_stats.get("avg_vocabulary_size", 0) if msg_stats else 0,
            "avg_punctuation_ratio": msg_stats.get("avg_punctuation_ratio", 0) if msg_stats else 0,
            "avg_sentiment": msg_stats.get("avg_sentiment") if msg_stats else None,
            "unique_words": word_stats.get("unique_words", 0) if word_stats else 0,
            "total_words": word_stats.get("total_words", 0) if word_stats else 0
        }
        
        return metrics
    
    async def get_vocabulary_overlap_series(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Get vocabulary overlap values over time.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of turn_number and vocabulary_overlap pairs
        """
        query = """
            SELECT turn_number, vocabulary_overlap
            FROM turn_metrics
            WHERE conversation_id = ? AND vocabulary_overlap IS NOT NULL
            ORDER BY turn_number
        """
        
        return await self.fetch_all(query, (conversation_id,))
    
    async def calculate_convergence_metrics(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Calculate convergence-related metrics.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Convergence metrics dictionary
        """
        # Get vocabulary overlap series
        overlap_series = await self.get_vocabulary_overlap_series(conversation_id)
        
        # Get message length variance series
        variance_query = """
            SELECT turn_number, message_length_variance
            FROM turn_metrics
            WHERE conversation_id = ? AND message_length_variance IS NOT NULL
            ORDER BY turn_number
        """
        variance_series = await self.fetch_all(variance_query, (conversation_id,))
        
        # Calculate convergence rates
        vocab_convergence_rate = 0.0
        if len(overlap_series) >= 2:
            # Simple linear regression slope
            x = [item["turn_number"] for item in overlap_series]
            y = [item["vocabulary_overlap"] for item in overlap_series]
            if len(x) > 1:
                n = len(x)
                sum_x = sum(x)
                sum_y = sum(y)
                sum_xy = sum(xi * yi for xi, yi in zip(x, y))
                sum_x2 = sum(xi * xi for xi in x)
                
                if n * sum_x2 - sum_x * sum_x != 0:
                    vocab_convergence_rate = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Calculate message length convergence (decreasing variance = convergence)
        length_convergence = 0.0
        if len(variance_series) >= 2:
            first_variance = variance_series[0]["message_length_variance"]
            last_variance = variance_series[-1]["message_length_variance"]
            if first_variance > 0:
                length_convergence = 1 - (last_variance / first_variance)
        
        # Overall convergence score
        overall_score = (vocab_convergence_rate + length_convergence) / 2
        
        return {
            "vocabulary_convergence_rate": vocab_convergence_rate,
            "message_length_convergence": length_convergence,
            "overall_convergence_score": overall_score,
            "total_turns_analyzed": len(overlap_series)
        }
    
    async def get_top_words(
        self,
        conversation_id: str,
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most frequent words.
        
        Args:
            conversation_id: Conversation ID
            agent_id: Optional agent filter
            limit: Number of top words to return
            
        Returns:
            List of words and frequencies
        """
        if agent_id:
            query = """
                SELECT word, SUM(frequency) as total_frequency
                FROM word_frequencies
                WHERE conversation_id = ? AND agent_id = ?
                GROUP BY word
                ORDER BY total_frequency DESC
                LIMIT ?
            """
            params = (conversation_id, agent_id, limit)
        else:
            query = """
                SELECT word, SUM(frequency) as total_frequency
                FROM word_frequencies
                WHERE conversation_id = ?
                GROUP BY word
                ORDER BY total_frequency DESC
                LIMIT ?
            """
            params = (conversation_id, limit)
        
        return await self.fetch_all(query, params)
    
    async def delete_metrics(self, conversation_id: str):
        """Delete all metrics for a conversation.
        
        Args:
            conversation_id: Conversation ID
        """
        # Delete from all metric tables
        await self.execute_query(
            "DELETE FROM turn_metrics WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        await self.execute_query(
            "DELETE FROM message_metrics WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        await self.execute_query(
            "DELETE FROM word_frequencies WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        logger.info(f"Deleted all metrics for conversation {conversation_id}")