"""Unified event store for all Pidgin storage needs."""

import json
import uuid
import asyncio
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import os

from .async_duckdb import AsyncDuckDB
from .schema import get_all_schemas
from ..io.logger import get_logger

logger = get_logger("event_store")


class EventStore:
    """The ONLY storage class in the entire codebase."""
    
    def __init__(self, db_path: Optional[Path] = None, read_only: bool = False):
        """Initialize the event store.
        
        Args:
            db_path: Path to DuckDB database. Defaults to ./pidgin_output/experiments/experiments.duckdb
            read_only: If True, skip schema initialization and use read-only operations
        """
        if db_path is None:
            # Use consistent path logic from paths module
            from ..io.paths import get_database_path
            db_path = get_database_path()
        
        self.db_path = Path(db_path).resolve()
        self.read_only = read_only
        
        if not self.read_only:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if database exists before creating AsyncDuckDB in read-only mode
        self._db_exists = self.db_path.exists()
        
        # Initialize async database only if not in read-only mode or if database exists
        if not self.read_only or self._db_exists:
            self.db = AsyncDuckDB(self.db_path, read_only=self.read_only)
        else:
            self.db = None
        
        # Sequence counter for events
        self._sequence = 0
        self._sequence_lock = asyncio.Lock()
        
        # Track initialization
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
        # Start batch processor for events (only if not read-only and db exists)
        if not self.read_only and self.db:
            self.db.start_batch_processor()
    
    async def initialize(self):
        """Initialize database schema."""
        # In read-only mode, check if database existed when we initialized
        if self.read_only:
            if not self._db_exists:
                raise FileNotFoundError(f"Database {self.db_path} does not exist. Cannot open in read-only mode.")
            self._initialized = True
            return
            
        async with self._init_lock:
            if self._initialized:
                return
            
            # Create all schemas
            for schema_sql in get_all_schemas():
                await self._retry_with_backoff(lambda: self.db.execute(schema_sql))
            
            self._initialized = True
            logger.info(f"Initialized database at {self.db_path}")
    
    async def close(self):
        """Close database connections."""
        if self.db:
            await self.db.close()
    
    async def _retry_with_backoff(self, func, max_retries=None):
        """Exponential backoff for all DB operations."""
        # If database doesn't exist in read-only mode, fail immediately
        if self.read_only and not self._db_exists:
            raise FileNotFoundError("Database does not exist")
        
        # Use fewer retries for read-only operations to fail fast
        if max_retries is None:
            max_retries = 1 if self.read_only else 3
            
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                # Check if this is a DuckDB concurrency error
                error_msg = str(e).lower()
                is_lock_error = any(phrase in error_msg for phrase in [
                    'database is locked',
                    'could not set lock',
                    'concurrent',
                    'another connection',
                    'conflicting lock'
                ])
                
                if attempt == max_retries - 1:
                    raise
                    
                # Use shorter retry for lock errors, longer for other errors
                if is_lock_error:
                    wait_time = 0.5 + random.uniform(0, 0.5)  # 0.5-1s for lock errors
                else:
                    wait_time = 2 ** attempt + random.uniform(0, 1)  # Exponential for other errors
                    
                logger.warning(f"DB operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    # ========== Event Sourcing ==========
    
    async def emit_event(self, event_type: str, conversation_id: Optional[str] = None,
                        experiment_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Emit an event to the event store with sequence number.
        
        Args:
            event_type: Type of event
            conversation_id: Optional conversation ID
            experiment_id: Optional experiment ID  
            data: Event data as dict
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()
        
        async with self._sequence_lock:
            self._sequence += 1
            sequence = self._sequence
        
        await self._retry_with_backoff(lambda: self.db.execute("""
            INSERT INTO events (event_type, conversation_id, experiment_id, event_data, sequence)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, conversation_id, experiment_id, json.dumps(data or {}), sequence)))
    
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
                   experiment_id, event_data, sequence
            FROM events
            {where_clause}
            ORDER BY sequence
        """
        
        return await self._retry_with_backoff(lambda: self.db.fetch_all(query, tuple(params)))
    
    # ========== Experiments ==========
    
    async def create_experiment(self, name: str, config: dict) -> str:
        """Create a new experiment.
        
        Args:
            name: Human-readable experiment name
            config: Experiment configuration including repetitions, models, etc.
            
        Returns:
            experiment_id: Unique identifier for the experiment
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()
        
        experiment_id = f"exp_{uuid.uuid4().hex[:8]}"
        total_conversations = config.get('repetitions', 1)
        
        await self._retry_with_backoff(lambda: self.db.execute("""
            INSERT INTO experiments (
                experiment_id, name, config, total_conversations, status
            ) VALUES (?, ?, ?, ?, 'created')
        """, (experiment_id, name, json.dumps(config), total_conversations)))
        
        # Emit event
        await self.emit_event(
            'ExperimentCreated',
            experiment_id=experiment_id,
            data={'name': name, 'config': config}
        )
        
        return experiment_id
    
    async def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details by ID.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Experiment dict or None if not found
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()
        
        # In read-only mode, if database didn't exist when we initialized, return None
        if self.read_only and not self._db_exists:
            return None
        
        return await self._retry_with_backoff(lambda: self.db.fetch_one(
            "SELECT * FROM experiments WHERE experiment_id = ?",
            (experiment_id,)
        ))
    
    async def update_experiment_status(self, experiment_id: str, status: str):
        """Update experiment status.
        
        Args:
            experiment_id: Experiment identifier
            status: New status (created, running, completed, failed, interrupted)
        """
        timestamp_field = {
            'running': 'started_at',
            'completed': 'completed_at',
            'failed': 'completed_at',
            'interrupted': 'completed_at'
        }.get(status)
        
        if timestamp_field:
            await self._retry_with_backoff(lambda: self.db.execute(f"""
                UPDATE experiments 
                SET status = ?, {timestamp_field} = CURRENT_TIMESTAMP
                WHERE experiment_id = ?
            """, (status, experiment_id)))
        else:
            await self._retry_with_backoff(lambda: self.db.execute("""
                UPDATE experiments 
                SET status = ?
                WHERE experiment_id = ?
            """, (status, experiment_id)))
        
        # Emit event
        await self.emit_event(
            'ExperimentStatusChanged',
            experiment_id=experiment_id,
            data={'status': status}
        )
    
    async def mark_running_conversations_failed(self, experiment_id: str):
        """Mark all running conversations in an experiment as failed.
        
        Args:
            experiment_id: Experiment identifier
        """
        await self._retry_with_backoff(lambda: self.db.execute("""
            UPDATE conversations 
            SET status = 'failed', 
                completed_at = CURRENT_TIMESTAMP,
                error_message = 'Experiment terminated'
            WHERE experiment_id = ? AND status = 'running'
        """, (experiment_id,)))
    
    async def list_experiments(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all experiments with optional status filter.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of experiment dictionaries
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()
        
        # In read-only mode, if database didn't exist when we initialized, return empty list
        if self.read_only and not self._db_exists:
            return []
        
        if status_filter:
            return await self._retry_with_backoff(lambda: self.db.fetch_all(
                "SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC",
                (status_filter,)
            ))
        else:
            return await self._retry_with_backoff(lambda: self.db.fetch_all(
                "SELECT * FROM experiments ORDER BY created_at DESC"
            ))
    
    # ========== Conversations ==========
    
    async def create_conversation(self, experiment_id: str, conversation_id: str, config: dict):
        """Create a new conversation within an experiment.
        
        Args:
            experiment_id: Parent experiment ID
            conversation_id: Unique conversation identifier
            config: Conversation-specific configuration
        """
        # Handle both old-style and new-style configs
        agent_a_model = config.get('agent_a_model', 'unknown')
        agent_b_model = config.get('agent_b_model', 'unknown')
        agent_a_provider = config.get('agent_a_provider')
        agent_b_provider = config.get('agent_b_provider')
        temperature_a = config.get('temperature_a')
        temperature_b = config.get('temperature_b')
        initial_prompt = config.get('initial_prompt', '')
        max_turns = config.get('max_turns', 10)
        first_speaker = config.get('first_speaker', 'agent_a')
        
        # Check if we have the extended schema
        result = await self.db.fetch_one("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('conversations') 
            WHERE name IN ('agent_a_provider', 'agent_b_provider')
        """)
        
        has_extended_schema = result['count'] == 2 if result else False
        
        if has_extended_schema:
            # Use extended schema
            await self._retry_with_backoff(lambda: self.db.execute("""
                INSERT INTO conversations (
                    conversation_id, experiment_id,
                    agent_a_model, agent_a_provider, agent_a_temperature,
                    agent_b_model, agent_b_provider, agent_b_temperature,
                    initial_prompt, max_turns, first_speaker
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, experiment_id,
                agent_a_model, agent_a_provider, temperature_a,
                agent_b_model, agent_b_provider, temperature_b,
                initial_prompt, max_turns, first_speaker
            )))
        else:
            # Use basic schema with config JSON
            await self._retry_with_backoff(lambda: self.db.execute("""
                INSERT INTO conversations (
                    conversation_id, experiment_id, config,
                    agent_a_model, agent_b_model, first_speaker
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, experiment_id, json.dumps(config),
                agent_a_model, agent_b_model, first_speaker
            )))
        
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
        """Update conversation status and final metrics.
        
        Args:
            conversation_id: Conversation identifier
            status: New status
            convergence_reason: Why conversation ended (if applicable)
            final_convergence_score: Final convergence score (if applicable)
            error_message: Error message (if failed)
        """
        # Get current conversation
        conv = await self._retry_with_backoff(lambda: self.db.fetch_one(
            "SELECT experiment_id, started_at FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ))
        
        if not conv:
            logger.error(f"Conversation {conversation_id} not found")
            return
        
        timestamp_field = {
            'running': 'started_at',
            'completed': 'completed_at',
            'failed': 'completed_at',
            'interrupted': 'completed_at'
        }.get(status)
        
        # Get total turns for the conversation
        turn_count_result = await self._retry_with_backoff(lambda: self.db.fetch_one(
            "SELECT COUNT(*) as count FROM turn_metrics WHERE conversation_id = ?",
            (conversation_id,)
        ))
        total_turns = turn_count_result['count'] if turn_count_result else 0
        
        # Build dynamic query based on provided fields
        updates = ["status = ?", "total_turns = ?"]
        params = [status, total_turns]
        
        if timestamp_field:
            updates.append(f"{timestamp_field} = CURRENT_TIMESTAMP")
        
        if convergence_reason is not None:
            updates.append("convergence_reason = ?")
            params.append(convergence_reason)
            
        if final_convergence_score is not None:
            updates.append("final_convergence_score = ?")
            params.append(final_convergence_score)
            
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        # Add conversation_id as last parameter
        params.append(conversation_id)
        
        query = f"UPDATE conversations SET {', '.join(updates)} WHERE conversation_id = ?"
        await self._retry_with_backoff(lambda: self.db.execute(query, tuple(params)))
        
        # Update experiment conversation counts
        if status in ['completed', 'failed', 'interrupted']:
            if status == 'failed':
                await self._retry_with_backoff(lambda: self.db.execute("""
                    UPDATE experiments 
                    SET failed_conversations = failed_conversations + 1
                    WHERE experiment_id = ?
                """, (conv['experiment_id'],)))
            else:
                await self._retry_with_backoff(lambda: self.db.execute("""
                    UPDATE experiments 
                    SET completed_conversations = completed_conversations + 1
                    WHERE experiment_id = ?
                """, (conv['experiment_id'],)))
        
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
                'total_turns': total_turns
            }
        )
    
    async def log_agent_name(self, conversation_id: str, agent_id: str, chosen_name: str, turn_number: int = 0):
        """Log a chosen agent name for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            agent_id: Either 'agent_a' or 'agent_b'
            chosen_name: The name chosen by the agent
            turn_number: Turn number when name was chosen (default: 0)
        """
        if agent_id not in ['agent_a', 'agent_b']:
            raise ValueError(f"Invalid agent_id: {agent_id}")
        
        column_name = f"{agent_id}_chosen_name"
        
        await self._retry_with_backoff(lambda: self.db.execute(
            f"UPDATE conversations SET {column_name} = ? WHERE conversation_id = ?",
            (chosen_name, conversation_id)
        ))
        
        # Emit event
        await self.emit_event(
            'AgentNameChosen',
            conversation_id=conversation_id,
            data={'agent_id': agent_id, 'chosen_name': chosen_name, 'turn_number': turn_number}
        )
    
    # ========== Metrics Logging ==========
    
    async def log_turn_metrics(self, conversation_id: str, turn_number: int, metrics: dict):
        """Log turn-level metrics (convergence, aggregates).
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            metrics: Dictionary of metrics
        """
        await self._retry_with_backoff(lambda: self.db.execute("""
            INSERT OR REPLACE INTO turn_metrics (
                conversation_id, turn_number, convergence_score,
                vocabulary_overlap, structural_similarity,
                topic_similarity, style_match, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            turn_number,
            metrics.get('convergence_score'),
            metrics.get('vocabulary_overlap'),
            metrics.get('structural_similarity'),
            metrics.get('topic_similarity'),
            metrics.get('style_match'),
            json.dumps(metrics)
        )))
        
        # Emit event
        await self.emit_event(
            'TurnMetricsLogged',
            conversation_id=conversation_id,
            data={
                'turn_number': turn_number,
                'convergence_score': metrics.get('convergence_score')
            }
        )
    
    async def log_message_metrics(self, conversation_id: str, turn_number: int,
                                agent_id: str, metrics: dict, response_time_ms: Optional[int] = None):
        """Log message-level metrics.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            agent_id: Agent identifier (agent_a or agent_b)
            metrics: Message metrics
            response_time_ms: Response time in milliseconds
        """
        await self._retry_with_backoff(lambda: self.db.execute("""
            INSERT INTO message_metrics (
                conversation_id, turn_number, agent_id,
                message_length, word_count, unique_words,
                type_token_ratio, avg_word_length,
                response_time_ms, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            turn_number,
            agent_id,
            metrics.get('message_length'),
            metrics.get('word_count'),
            metrics.get('unique_words'),
            metrics.get('type_token_ratio'),
            metrics.get('avg_word_length'),
            response_time_ms,
            json.dumps(metrics)
        )))
    
    async def log_word_frequencies(self, conversation_id: str, turn_number: int,
                                 agent_id: str, word_frequencies: Dict[str, int]):
        """Log word frequencies for vocabulary analysis.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            agent_id: Agent identifier
            word_frequencies: Dict of word -> count
        """
        # Use executemany for efficiency
        data = [
            (conversation_id, turn_number, agent_id, word, freq)
            for word, freq in word_frequencies.items()
        ]
        
        await self._retry_with_backoff(lambda: self.db.executemany("""
            INSERT INTO word_frequencies (
                conversation_id, turn_number, agent_id, word, frequency
            ) VALUES (?, ?, ?, ?, ?)
        """, data))
    
    async def log_message(self, conversation_id: str, turn_number: int,
                        agent_id: str, content: str, tokens: Dict[str, int]):
        """Log message content for search and analysis.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            agent_id: Agent identifier
            content: Message content
            tokens: Token usage info
        """
        await self._retry_with_backoff(lambda: self.db.execute("""
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
        )))
    
    async def log_token_usage(self, conversation_id: str, provider: str, model: str,
                            usage: Dict[str, int], rate_limits: Dict[str, Any],
                            cost: Dict[str, float]):
        """Log token usage for cost tracking.
        
        Args:
            conversation_id: Conversation identifier
            provider: Provider name
            model: Model name
            usage: Token usage stats
            rate_limits: Rate limit info
            cost: Cost breakdown
        """
        await self._retry_with_backoff(lambda: self.db.execute("""
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
        )))
    
    # ========== Analytics Queries ==========
    
    async def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for an experiment.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Dictionary of aggregated metrics
        """
        # Get convergence distribution
        conv_result = await self._retry_with_backoff(lambda: self.db.fetch_one("""
            SELECT 
                MIN(convergence_score) as min_conv,
                MAX(convergence_score) as max_conv,
                AVG(convergence_score) as avg_conv,
                COUNT(DISTINCT conversation_id) as conv_count
            FROM turn_metrics
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations 
                WHERE experiment_id = ?
            )
        """, (experiment_id,)))
        
        # Get vocabulary overlap distribution
        overlap_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT 
                turn_number,
                AVG(vocabulary_overlap) as avg_overlap
            FROM turn_metrics
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations 
                WHERE experiment_id = ?
            )
            GROUP BY turn_number
            ORDER BY turn_number
        """, (experiment_id,)))
        
        overlap_dist = {row['turn_number']: row['avg_overlap'] for row in overlap_rows}
        
        # Get message length trends
        length_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT 
                turn_number,
                AVG(message_length) as avg_length
            FROM message_metrics
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations 
                WHERE experiment_id = ?
            )
            GROUP BY turn_number
            ORDER BY turn_number
        """, (experiment_id,)))
        
        length_dist = {row['turn_number']: row['avg_length'] for row in length_rows}
        
        # Get most common words across turns
        word_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT 
                word,
                SUM(frequency) as total_freq,
                COUNT(DISTINCT turn_number) as turn_count
            FROM word_frequencies
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations 
                WHERE experiment_id = ?
            )
            GROUP BY word
            ORDER BY total_freq DESC
            LIMIT 20
        """, (experiment_id,)))
        
        # Get words that emerge in later turns
        late_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT word, MIN(turn_number) as first_turn
            FROM word_frequencies
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations 
                WHERE experiment_id = ?
            )
            GROUP BY word
            HAVING first_turn > 5
            ORDER BY first_turn
            LIMIT 10
        """, (experiment_id,)))
        
        late_words = [(row['word'], row['first_turn']) for row in late_rows]
        
        # Get temperature effects if varied
        temp_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT 
                c.config->>'$.temperature_a' as temperature,
                AVG(tm.vocabulary_overlap) as avg_overlap
            FROM conversations c
            JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
            WHERE c.experiment_id = ?
            GROUP BY temperature
            HAVING temperature IS NOT NULL
        """, (experiment_id,)))
        
        temp_effects = {str(row['temperature']): row['avg_overlap'] 
                       for row in temp_rows} if temp_rows else None
        
        return {
            'convergence_stats': {
                'min': conv_result['min_conv'] if conv_result else None,
                'max': conv_result['max_conv'] if conv_result else None,
                'avg': conv_result['avg_conv'] if conv_result else None,
                'conversation_count': conv_result['conv_count'] if conv_result else 0
            },
            'overlap_by_turn': overlap_dist,
            'length_by_turn': length_dist,
            'top_words': [(row['word'], row['total_freq']) for row in word_rows],
            'emergent_words': late_words,
            'temperature_effects': temp_effects
        }
    
    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get full conversation history with metrics.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of turns with messages and metrics
        """
        # Get turn metrics
        turn_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT * FROM turn_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number
        """, (conversation_id,)))
        
        # Get message metrics
        msg_rows = await self._retry_with_backoff(lambda: self.db.fetch_all("""
            SELECT * FROM message_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number, agent_id
        """, (conversation_id,)))
        
        # Organize by turn
        turns = []
        for turn_row in turn_rows:
            turn_num = turn_row['turn_number']
            
            # Get messages for this turn
            turn_messages = [
                msg_row for msg_row in msg_rows 
                if msg_row['turn_number'] == turn_num
            ]
            
            turns.append({
                'turn_number': turn_num,
                'metrics': turn_row,
                'messages': turn_messages
            })
        
        return turns
    
    async def search_messages(self, query: str, experiment_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search messages using pattern matching.
        
        Args:
            query: Search query
            experiment_id: Optional experiment filter
            
        Returns:
            List of matching messages
        """
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
        
        return await self._retry_with_backoff(lambda: self.db.fetch_all(base_query, tuple(params)))