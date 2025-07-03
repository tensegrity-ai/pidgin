# pidgin/experiments/storage.py
"""Storage layer for Pidgin experiments using DuckDB."""

import os
import json
import duckdb
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

class ExperimentStore:
    """DuckDB storage for conversation experiments and metrics."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the experiment store.
        
        Args:
            db_path: Path to DuckDB database. Defaults to ./pidgin_output/experiments/experiments.duckdb
        """
        if db_path is None:
            # Always resolve to absolute path for consistency
            project_base = os.environ.get('PIDGIN_PROJECT_BASE', os.getcwd())
            db_path = Path(project_base).resolve() / "pidgin_output" / "experiments" / "experiments.duckdb"
        
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database with clean schema."""
        conn = duckdb.connect(str(self.db_path))
        try:
            # Create tables directly
            self._create_tables(conn)
        finally:
            conn.close()
    
    def _create_tables(self, conn):
        """Create all experiment tables with clean schema."""
        # Experiments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'created',
                config JSON NOT NULL,
                total_conversations INTEGER NOT NULL,
                completed_conversations INTEGER DEFAULT 0,
                failed_conversations INTEGER DEFAULT 0,
                metadata JSON
            )
        """)
        
        # Conversations table with foreign key
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'created',
                config JSON NOT NULL,
                first_speaker TEXT DEFAULT 'agent_a',
                agent_a_model TEXT NOT NULL,
                agent_b_model TEXT NOT NULL,
                agent_a_chosen_name TEXT,
                agent_b_chosen_name TEXT,
                total_turns INTEGER DEFAULT 0,
                convergence_reason TEXT,
                final_convergence_score REAL,
                error_message TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)
        
        # Turn metrics table 
        conn.execute("""
            CREATE TABLE IF NOT EXISTS turn_metrics (
                id INTEGER PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                convergence_score REAL,
                vocabulary_overlap REAL,
                structural_similarity REAL,
                topic_similarity REAL,
                style_match REAL,
                metrics_json JSON,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                UNIQUE(conversation_id, turn_number)
            )
        """)
        
        # Create sequence for turn_metrics id
        conn.execute("CREATE SEQUENCE IF NOT EXISTS turn_metrics_id_seq")
        
        # Message metrics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_metrics (
                id INTEGER PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                message_length INTEGER,
                word_count INTEGER,
                unique_words INTEGER,
                type_token_ratio REAL,
                avg_word_length REAL,
                response_time_ms INTEGER,
                metrics_json JSON,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Create sequence for message_metrics id
        conn.execute("CREATE SEQUENCE IF NOT EXISTS message_metrics_id_seq")
        
        # Word frequency table for vocabulary analysis
        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_frequencies (
                id INTEGER PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                word TEXT NOT NULL,
                frequency INTEGER,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Create sequence for word_frequencies id
        conn.execute("CREATE SEQUENCE IF NOT EXISTS word_frequencies_id_seq")
        
        # Create indices for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_experiment ON conversations(experiment_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_metrics_conversation ON turn_metrics(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_message_metrics_conversation ON message_metrics(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_word_frequencies_conversation ON word_frequencies(conversation_id)")
    
    def _get_connection(self):
        """Get database connection."""
        # DuckDB returns dictionaries by default
        return duckdb.connect(str(self.db_path))
    
    def _row_to_dict(self, result) -> Optional[Dict[str, Any]]:
        """Convert DuckDB result to dictionary."""
        if not result:
            return None
        # DuckDB fetchone() returns a tuple, fetchall() returns list of tuples
        # We need to get column names from the result description
        return result.fetchone()  # DuckDB's fetchone returns dict-like object
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details by ID.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Experiment dict or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,)
            ).fetchone()
            
            if row:
                # DuckDB returns tuples, convert to dict
                columns = [desc[0] for desc in conn.description]
                return dict(zip(columns, row))
            return None
    
    def create_experiment(self, name: str, config: dict) -> str:
        """Create a new experiment.
        
        Args:
            name: Human-readable experiment name
            config: Experiment configuration including repetitions, models, etc.
            
        Returns:
            experiment_id: Unique identifier for the experiment
        """
        experiment_id = f"exp_{uuid.uuid4().hex[:8]}"
        total_conversations = config.get('repetitions', 1)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO experiments (
                    experiment_id, name, config, total_conversations, status
                ) VALUES (?, ?, ?, ?, 'created')
            """, (experiment_id, name, json.dumps(config), total_conversations))
            conn.commit()
        
        return experiment_id
    
    def update_experiment_status(self, experiment_id: str, status: str):
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
        
        with self._get_connection() as conn:
            if timestamp_field:
                conn.execute(f"""
                    UPDATE experiments 
                    SET status = ?, {timestamp_field} = CURRENT_TIMESTAMP
                    WHERE experiment_id = ?
                """, (status, experiment_id))
            else:
                conn.execute("""
                    UPDATE experiments 
                    SET status = ?
                    WHERE experiment_id = ?
                """, (status, experiment_id))
            conn.commit()
    
    def mark_running_conversations_failed(self, experiment_id: str):
        """Mark all running conversations in an experiment as failed.
        
        Args:
            experiment_id: Experiment identifier
        """
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE conversations 
                SET status = 'failed', 
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = 'Experiment terminated'
                WHERE experiment_id = ? AND status = 'running'
            """, (experiment_id,))
            conn.commit()
    
    def create_conversation(self, experiment_id: str, conversation_id: str, config: dict):
        """Create a new conversation within an experiment.
        
        Args:
            experiment_id: Parent experiment ID
            conversation_id: Unique conversation identifier
            config: Conversation-specific configuration
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO conversations (
                    conversation_id, experiment_id, config,
                    agent_a_model, agent_b_model, first_speaker
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                experiment_id,
                json.dumps(config),
                config.get('agent_a_model', 'unknown'),
                config.get('agent_b_model', 'unknown'),
                config.get('first_speaker', 'agent_a')
            ))
            conn.commit()
    
    def update_conversation_status(self, conversation_id: str, status: str,
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
        timestamp_field = {
            'running': 'started_at',
            'completed': 'completed_at',
            'failed': 'completed_at',
            'interrupted': 'completed_at'
        }.get(status)
        
        with self._get_connection() as conn:
            # Build dynamic query based on provided fields
            updates = ["status = ?"]
            params = [status]
            
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
            
            # Get total turns for the conversation
            turn_count = conn.execute(
                "SELECT COUNT(*) as count FROM turn_metrics WHERE conversation_id = ?",
                (conversation_id,)
            ).fetchone()['count']
            
            updates.append("total_turns = ?")
            params.append(turn_count)
            
            # Add conversation_id as last parameter
            params.append(conversation_id)
            
            query = f"UPDATE conversations SET {', '.join(updates)} WHERE conversation_id = ?"
            conn.execute(query, params)
            
            # Update experiment conversation counts
            if status in ['completed', 'failed', 'interrupted']:
                if status == 'failed':
                    conn.execute("""
                        UPDATE experiments 
                        SET failed_conversations = failed_conversations + 1
                        WHERE experiment_id = (
                            SELECT experiment_id FROM conversations 
                            WHERE conversation_id = ?
                        )
                    """, (conversation_id,))
                else:
                    conn.execute("""
                        UPDATE experiments 
                        SET completed_conversations = completed_conversations + 1
                        WHERE experiment_id = (
                            SELECT experiment_id FROM conversations 
                            WHERE conversation_id = ?
                        )
                    """, (conversation_id,))
            
            conn.commit()
    
    def log_agent_name(self, conversation_id: str, agent_id: str, chosen_name: str, turn_number: int = 0):
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
        
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE conversations SET {column_name} = ? WHERE conversation_id = ?",
                (chosen_name, conversation_id)
            )
            conn.commit()
        
    def log_turn_metrics(self, conversation_id: str, turn_number: int, metrics: dict):
        """Log turn-level metrics (convergence, aggregates).
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            metrics: Dictionary of metrics
        """
        with self._get_connection() as conn:
            conn.execute("""
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
            ))
            conn.commit()
    
    def log_message_metrics(self, conversation_id: str, turn_number: int,
                          agent_id: str, metrics: dict, response_time_ms: Optional[int] = None):
        """Log message-level metrics.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            agent_id: Agent identifier (agent_a or agent_b)
            metrics: Message metrics
            response_time_ms: Response time in milliseconds
        """
        with self._get_connection() as conn:
            conn.execute("""
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
            ))
            conn.commit()
    
    def log_word_frequencies(self, conversation_id: str, turn_number: int,
                           agent_id: str, word_frequencies: Dict[str, int]):
        """Log word frequencies for vocabulary analysis.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            agent_id: Agent identifier
            word_frequencies: Dict of word -> count
        """
        with self._get_connection() as conn:
            # Use executemany for efficiency
            data = [
                (conversation_id, turn_number, agent_id, word, freq)
                for word, freq in word_frequencies.items()
            ]
            
            conn.executemany("""
                INSERT INTO word_frequencies (
                    conversation_id, turn_number, agent_id, word, frequency
                ) VALUES (?, ?, ?, ?, ?)
            """, data)
            conn.commit()
    
    def list_experiments(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all experiments with optional status filter.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of experiment dictionaries
        """
        with self._get_connection() as conn:
            if status_filter:
                rows = conn.execute(
                    "SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC",
                    (status_filter,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiments ORDER BY created_at DESC"
                ).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_experiment_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for an experiment.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Dictionary of aggregated metrics
        """
        with self._get_connection() as conn:
            # Get convergence distribution
            conv_query = """
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
            """
            conv_row = conn.execute(conv_query, (experiment_id,)).fetchone()
            
            # Get vocabulary overlap distribution
            overlap_query = """
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
            """
            overlap_rows = conn.execute(overlap_query, (experiment_id,)).fetchall()
            overlap_dist = {row['turn_number']: row['avg_overlap'] 
                          for row in overlap_rows}
            
            # Get message length trends
            length_query = """
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
            """
            length_rows = conn.execute(length_query, (experiment_id,)).fetchall()
            length_dist = {row['turn_number']: row['avg_length'] 
                         for row in length_rows}
            
            # Get most common words across turns
            word_query = """
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
            """
            word_rows = conn.execute(word_query, (experiment_id,)).fetchall()
            
            # Get words that emerge in later turns
            late_words_query = """
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
            """
            late_rows = conn.execute(late_words_query, (experiment_id,)).fetchall()
            late_words = [(row['word'], row['first_turn']) for row in late_rows]
            
            # Get temperature effects if varied
            temp_query = """
                SELECT 
                    c.config->>'$.temperature_a' as temperature,
                    AVG(tm.vocabulary_overlap) as avg_overlap
                FROM conversations c
                JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
                WHERE c.experiment_id = ?
                GROUP BY temperature
                HAVING temperature IS NOT NULL
            """
            temp_rows = conn.execute(temp_query, (experiment_id,)).fetchall()
            temp_effects = {str(row['temperature']): row['avg_overlap'] 
                          for row in temp_rows} if temp_rows else None
            
            return {
                'convergence_stats': {
                    'min': conv_row['min_conv'],
                    'max': conv_row['max_conv'],
                    'avg': conv_row['avg_conv'],
                    'conversation_count': conv_row['conv_count']
                },
                'overlap_by_turn': overlap_dist,
                'length_by_turn': length_dist,
                'top_words': [(row['word'], row['total_freq']) for row in word_rows],
                'emergent_words': late_words,
                'temperature_effects': temp_effects
            }
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get full conversation history with metrics.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of turns with messages and metrics
        """
        with self._get_connection() as conn:
            # Get turn metrics
            turn_query = """
                SELECT * FROM turn_metrics
                WHERE conversation_id = ?
                ORDER BY turn_number
            """
            turn_rows = conn.execute(turn_query, (conversation_id,)).fetchall()
            
            # Get message metrics
            msg_query = """
                SELECT * FROM message_metrics
                WHERE conversation_id = ?
                ORDER BY turn_number, agent_id
            """
            msg_rows = conn.execute(msg_query, (conversation_id,)).fetchall()
            
            # Organize by turn
            turns = []
            for turn_row in turn_rows:
                turn_num = turn_row['turn_number']
                
                # Get messages for this turn
                turn_messages = [
                    dict(row) for row in msg_rows 
                    if row['turn_number'] == turn_num
                ]
                
                turns.append({
                    'turn_number': turn_num,
                    'metrics': dict(turn_row),
                    'messages': turn_messages
                })
            
            return turns
