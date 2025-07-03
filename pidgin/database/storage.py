"""Async storage layer for experiments using DuckDB with advanced features."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import os

from .async_duckdb import AsyncDuckDB
from .schema import get_all_schemas
from ..io.logger import get_logger

logger = get_logger("storage")


class AsyncExperimentStore:
    """Async DuckDB storage leveraging advanced features."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize async experiment store.
        
        Args:
            db_path: Path to DuckDB database
        """
        if db_path is None:
            project_base = os.environ.get('PIDGIN_PROJECT_BASE', os.getcwd())
            db_path = Path(project_base).resolve() / "pidgin_output" / "experiments" / "experiments.duckdb"
        
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize async database
        self.db = AsyncDuckDB(self.db_path)
        
        # Start batch processor for events
        self.db.start_batch_processor()
    
    async def initialize(self):
        """Initialize database schema."""
        # Create all schemas
        for schema_sql in get_all_schemas():
            await self.db.execute(schema_sql)
        
        logger.info(f"Initialized database at {self.db_path}")
    
    async def close(self):
        """Close database connections."""
        await self.db.close()
    
    # ========== Event Sourcing ==========
    
    async def emit_event(self, event_type: str, conversation_id: Optional[str] = None,
                        experiment_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Emit an event to the event store.
        
        Args:
            event_type: Type of event
            conversation_id: Optional conversation ID
            experiment_id: Optional experiment ID  
            data: Event data as dict
        """
        await self.db.execute("""
            INSERT INTO events (event_type, conversation_id, experiment_id, event_data)
            VALUES (?, ?, ?, ?)
        """, (event_type, conversation_id, experiment_id, json.dumps(data or {})))
    
    async def get_events(self, conversation_id: Optional[str] = None,
                        experiment_id: Optional[str] = None,
                        event_type: Optional[str] = None,
                        since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Query events with filters.
        
        Args:
            conversation_id: Filter by conversation
            experiment_id: Filter by experiment
            event_type: Filter by event type
            since: Filter events after this timestamp
            
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
            
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
            
        if since:
            conditions.append("timestamp > ?")
            params.append(since)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT event_id, timestamp, event_type, conversation_id, 
                   experiment_id, event_data
            FROM events
            {where_clause}
            ORDER BY timestamp
        """
        
        return await self.db.fetch_all(query, tuple(params))
    
    # ========== Experiments ==========
    
    async def create_experiment(self, name: str, config: Dict[str, Any]) -> str:
        """Create a new experiment.
        
        Args:
            name: Experiment name
            config: Experiment configuration
            
        Returns:
            experiment_id
        """
        experiment_id = f"exp_{uuid.uuid4().hex[:8]}"
        
        # Extract config values
        repetitions = config.get('repetitions', 1)
        max_turns = config.get('max_turns', 10)
        initial_prompt = config.get('initial_prompt', '')
        convergence_threshold = config.get('convergence_threshold')
        temperature_a = config.get('temperature_a')
        temperature_b = config.get('temperature_b')
        
        await self.db.execute("""
            INSERT INTO experiments (
                experiment_id, name, config, total_conversations
            ) VALUES (?, ?, ?, ?)
        """, (
            experiment_id,
            name,
            json.dumps({
                'repetitions': repetitions,
                'max_turns': max_turns,
                'initial_prompt': initial_prompt,
                'convergence_threshold': convergence_threshold,
                'temperature_a': temperature_a,
                'temperature_b': temperature_b
            }),
            repetitions
        ))
        
        # Emit event
        await self.emit_event(
            'ExperimentCreated',
            experiment_id=experiment_id,
            data={'name': name, 'config': config}
        )
        
        return experiment_id
    
    async def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID."""
        return await self.db.fetch_one(
            "SELECT * FROM experiments WHERE experiment_id = ?",
            (experiment_id,)
        )
    
    async def update_experiment_status(self, experiment_id: str, status: str):
        """Update experiment status."""
        timestamp_field = {
            'running': 'started_at',
            'completed': 'completed_at',
            'failed': 'completed_at',
            'interrupted': 'completed_at'
        }.get(status)
        
        if timestamp_field:
            await self.db.execute(f"""
                UPDATE experiments 
                SET status = ?, {timestamp_field} = CURRENT_TIMESTAMP
                WHERE experiment_id = ?
            """, (status, experiment_id))
        else:
            await self.db.execute(
                "UPDATE experiments SET status = ? WHERE experiment_id = ?",
                (status, experiment_id)
            )
        
        # Emit event
        await self.emit_event(
            'ExperimentStatusChanged',
            experiment_id=experiment_id,
            data={'status': status}
        )
    
    async def list_experiments(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List experiments with optional status filter."""
        if status:
            return await self.db.fetch_all(
                "SELECT * FROM experiment_dashboard WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            return await self.db.fetch_all(
                "SELECT * FROM experiment_dashboard ORDER BY created_at DESC"
            )
    
    # ========== Conversations ==========
    
    async def create_conversation(self, experiment_id: str, conversation_id: str, 
                                 config: Dict[str, Any]):
        """Create a new conversation."""
        await self.db.execute("""
            INSERT INTO conversations (
                conversation_id, experiment_id,
                agent_a_model, agent_a_provider, agent_a_temperature,
                agent_b_model, agent_b_provider, agent_b_temperature,
                initial_prompt, max_turns, first_speaker
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            experiment_id,
            config.get('agent_a_model', 'unknown'),
            config.get('agent_a_provider'),
            config.get('temperature_a'),
            config.get('agent_b_model', 'unknown'),
            config.get('agent_b_provider'),
            config.get('temperature_b'),
            config.get('initial_prompt', ''),
            config.get('max_turns', 10),
            config.get('first_speaker', 'agent_a')
        ))
        
        # Emit event
        await self.emit_event(
            'ConversationCreated',
            conversation_id=conversation_id,
            experiment_id=experiment_id,
            data=config
        )
    
    async def update_conversation_status(self, conversation_id: str, status: str,
                                       convergence_reason: Optional[str] = None,
                                       final_convergence_score: Optional[float] = None,
                                       error_message: Optional[str] = None):
        """Update conversation status with final metrics."""
        # Get current conversation
        conv = await self.db.fetch_one(
            "SELECT experiment_id, started_at FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        if not conv:
            logger.error(f"Conversation {conversation_id} not found")
            return
        
        # Calculate duration if completing
        duration_ms = None
        if status in ['completed', 'failed', 'interrupted'] and conv['started_at']:
            duration_ms = int((datetime.now() - conv['started_at']).total_seconds() * 1000)
        
        # Get turn count
        turn_count_result = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM turn_metrics WHERE conversation_id = ?",
            (conversation_id,)
        )
        total_turns = turn_count_result['count'] if turn_count_result else 0
        
        # Update conversation
        await self.db.execute("""
            UPDATE conversations 
            SET status = ?,
                total_turns = ?,
                final_convergence_score = ?,
                convergence_reason = ?,
                duration_ms = ?,
                error_message = ?,
                error_type = ?,
                error_timestamp = ?,
                completed_at = CASE WHEN ? IN ('completed', 'failed', 'interrupted') 
                              THEN CURRENT_TIMESTAMP ELSE completed_at END,
                started_at = CASE WHEN ? = 'running' AND started_at IS NULL
                            THEN CURRENT_TIMESTAMP ELSE started_at END
            WHERE conversation_id = ?
        """, (
            status,
            total_turns,
            final_convergence_score,
            convergence_reason,
            duration_ms,
            error_message,
            'error' if error_message else None,
            datetime.now() if error_message else None,
            status,
            status,
            conversation_id
        ))
        
        # Update experiment progress
        if status in ['completed', 'failed', 'interrupted']:
            if status == 'failed':
                await self.db.execute("""
                    UPDATE experiments 
                    SET failed_conversations = failed_conversations + 1
                    WHERE experiment_id = ?
                """, (conv['experiment_id'],))
            else:
                await self.db.execute("""
                    UPDATE experiments 
                    SET completed_conversations = completed_conversations + 1
                    WHERE experiment_id = ?
                """, (conv['experiment_id'],))
        
        # Emit event
        await self.emit_event(
            'ConversationStatusChanged',
            conversation_id=conversation_id,
            experiment_id=conv['experiment_id'],
            data={
                'status': status,
                'convergence_reason': convergence_reason,
                'final_convergence_score': final_convergence_score,
                'error_message': error_message,
                'total_turns': total_turns,
                'duration_ms': duration_ms
            }
        )
    
    async def log_agent_name(self, conversation_id: str, agent_id: str, chosen_name: str):
        """Log agent's chosen name."""
        if agent_id not in ['agent_a', 'agent_b']:
            raise ValueError(f"Invalid agent_id: {agent_id}")
        
        field = f"{agent_id}_chosen_name"
        
        await self.db.execute(f"""
            UPDATE conversations 
            SET {field} = ?
            WHERE conversation_id = ?
        """, (chosen_name, conversation_id))
        
        # Emit event
        await self.emit_event(
            'AgentNameChosen',
            conversation_id=conversation_id,
            data={'agent_id': agent_id, 'chosen_name': chosen_name}
        )
    
    # ========== Turn Metrics ==========
    
    async def log_turn_metrics(self, conversation_id: str, turn_number: int,
                              metrics: Dict[str, Any], word_frequencies: Dict[str, Dict[str, int]],
                              message_metrics: Dict[str, Dict[str, Any]],
                              timing: Dict[str, Any]):
        """Log comprehensive turn metrics using native DuckDB types."""
        await self.db.execute("""
            INSERT INTO turn_metrics (
                conversation_id, turn_number,
                convergence_score, vocabulary_overlap, structural_similarity,
                topic_similarity, style_match,
                word_frequencies_a, word_frequencies_b, shared_vocabulary,
                message_a_length, message_a_word_count, message_a_unique_words,
                message_a_type_token_ratio, message_a_avg_word_length, message_a_response_time_ms,
                message_b_length, message_b_word_count, message_b_unique_words,
                message_b_type_token_ratio, message_b_avg_word_length, message_b_response_time_ms,
                turn_start_time, turn_end_time, duration_ms,
                extended_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            turn_number,
            metrics.get('convergence_score'),
            metrics.get('vocabulary_overlap'),
            metrics.get('structural_similarity'),
            metrics.get('topic_similarity'),
            metrics.get('style_match'),
            json.dumps(word_frequencies.get('agent_a', {})),
            json.dumps(word_frequencies.get('agent_b', {})),
            json.dumps(word_frequencies.get('shared', {})),
            message_metrics.get('agent_a', {}).get('length'),
            message_metrics.get('agent_a', {}).get('word_count'),
            message_metrics.get('agent_a', {}).get('unique_words'),
            message_metrics.get('agent_a', {}).get('type_token_ratio'),
            message_metrics.get('agent_a', {}).get('avg_word_length'),
            message_metrics.get('agent_a', {}).get('response_time_ms'),
            message_metrics.get('agent_b', {}).get('length'),
            message_metrics.get('agent_b', {}).get('word_count'),
            message_metrics.get('agent_b', {}).get('unique_words'),
            message_metrics.get('agent_b', {}).get('type_token_ratio'),
            message_metrics.get('agent_b', {}).get('avg_word_length'),
            message_metrics.get('agent_b', {}).get('response_time_ms'),
            timing.get('turn_start'),
            timing.get('turn_end'),
            timing.get('duration_ms'),
            json.dumps(metrics.get('extended', {}))
        ))
        
        # Emit event
        await self.emit_event(
            'TurnMetricsLogged',
            conversation_id=conversation_id,
            data={
                'turn_number': turn_number,
                'convergence_score': metrics.get('convergence_score')
            }
        )
    
    async def log_message(self, conversation_id: str, turn_number: int,
                         agent_id: str, content: str, tokens: Dict[str, int]):
        """Log message content for search and analysis."""
        await self.db.execute("""
            INSERT INTO messages (
                conversation_id, turn_number, agent_id, content, 
                token_count, model_reported_tokens
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            turn_number,
            agent_id,
            content,
            tokens.get('count', 0),
            tokens.get('model_reported', 0)
        ))
    
    async def log_token_usage(self, conversation_id: str, provider: str, model: str,
                             usage: Dict[str, int], rate_limits: Dict[str, Any],
                             cost: Dict[str, float]):
        """Log token usage for cost tracking."""
        await self.db.execute("""
            INSERT INTO token_usage (
                conversation_id, provider, model,
                prompt_tokens, completion_tokens, total_tokens,
                requests_per_minute, tokens_per_minute, 
                current_rpm_usage, current_tpm_usage,
                prompt_cost, completion_cost, total_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            provider,
            model,
            usage.get('prompt_tokens', 0),
            usage.get('completion_tokens', 0),
            usage.get('total_tokens', 0),
            rate_limits.get('requests_per_minute'),
            rate_limits.get('tokens_per_minute'),
            rate_limits.get('current_rpm_usage'),
            rate_limits.get('current_tpm_usage'),
            cost.get('prompt_cost', 0.0),
            cost.get('completion_cost', 0.0),
            cost.get('total_cost', 0.0)
        ))
    
    # ========== Analytics Queries ==========
    
    async def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get comprehensive experiment metrics using views."""
        # Get dashboard metrics
        dashboard = await self.db.fetch_one(
            "SELECT * FROM experiment_dashboard WHERE experiment_id = ?",
            (experiment_id,)
        )
        
        # Get convergence distribution
        convergence_dist = await self.db.fetch_all("""
            SELECT 
                turn_number,
                AVG(convergence_score) as avg_convergence,
                STDDEV(convergence_score) as stddev_convergence,
                COUNT(*) as sample_size
            FROM convergence_trends
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations WHERE experiment_id = ?
            )
            GROUP BY turn_number
            ORDER BY turn_number
        """, (experiment_id,))
        
        # Get vocabulary evolution
        vocab_evolution = await self.db.fetch_all("""
            SELECT 
                turn_number,
                AVG(shared_vocab_size) as avg_shared_vocab,
                AVG(vocab_size_a + vocab_size_b) as avg_total_vocab
            FROM convergence_trends
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations WHERE experiment_id = ?
            )
            GROUP BY turn_number
            ORDER BY turn_number
        """, (experiment_id,))
        
        # Get vocabulary size trends (simplified for now)
        top_words = []
        
        return {
            'summary': dashboard,
            'convergence_by_turn': convergence_dist,
            'vocabulary_evolution': vocab_evolution,
            'top_shared_words': top_words
        }
    
    async def search_messages(self, query: str, experiment_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search messages using pattern matching."""
        base_query = """
            SELECT 
                m.conversation_id,
                m.turn_number,
                m.agent_id,
                m.content,
                c.experiment_id
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.conversation_id
            WHERE m.content LIKE ?
        """
        
        params = [f"%{query}%"]
        
        if experiment_id:
            base_query += " AND c.experiment_id = ?"
            params.append(experiment_id)
        
        base_query += " ORDER BY m.conversation_id, m.turn_number"
        
        return await self.db.fetch_all(base_query, tuple(params))