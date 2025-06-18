"""Storage layer for Pidgin experiments using SQLite."""

import os
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

class ExperimentStore:
    """SQLite storage for conversation experiments and metrics."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the experiment store.
        
        Args:
            db_path: Path to SQLite database. Defaults to ./pidgin_output/experiments/experiments.db
        """
        if db_path is None:
            # Check if we're in a daemon context
            project_base = os.environ.get('PIDGIN_PROJECT_BASE')
            if project_base:
                # Use the preserved project base path
                db_path = Path(project_base) / "pidgin_output" / "experiments" / "experiments.db"
            else:
                # Normal operation - use actual current working directory
                cwd = Path(os.getcwd())
                db_path = cwd / "pidgin_output" / "experiments" / "experiments.db"
        
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database with clean schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create tables directly
            self._create_tables(conn)
    
    def _create_tables(self, conn):
        """Create all experiment tables with clean schema."""
        
        # Drop old mixed table if it exists
        conn.execute("DROP TABLE IF EXISTS turns")
        
        # Experiments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'created' CHECK (status IN ('created', 'running', 'completed', 'failed')),
                config JSON NOT NULL,
                total_conversations INTEGER NOT NULL,
                completed_conversations INTEGER DEFAULT 0,
                failed_conversations INTEGER DEFAULT 0,
                metadata JSON
            )
        """)
        
        # Conversations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'created' CHECK (status IN ('created', 'running', 'completed', 'failed', 'interrupted')),
                config JSON NOT NULL,
                first_speaker TEXT DEFAULT 'agent_a' CHECK (first_speaker IN ('agent_a', 'agent_b')),
                agent_a_model TEXT NOT NULL,
                agent_b_model TEXT NOT NULL,
                agent_a_chosen_name TEXT,
                agent_b_chosen_name TEXT,
                total_turns INTEGER DEFAULT 0,
                convergence_reason TEXT,
                final_convergence_score REAL,
                error_message TEXT,
                metadata JSON,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)
        
        # Turn metrics table (one row per turn)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS turn_metrics (
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Convergence metrics
                convergence_score REAL,
                vocabulary_overlap REAL,
                length_ratio REAL,
                structural_similarity REAL,
                cross_repetition_score REAL,
                mimicry_score REAL,
                
                -- Turn-level aggregates
                total_words INTEGER,
                total_sentences INTEGER,
                combined_vocabulary_size INTEGER,
                
                -- Timing
                turn_duration_ms INTEGER,
                agent_a_response_time_ms INTEGER,
                agent_b_response_time_ms INTEGER,
                
                -- Additional metrics as JSON
                additional_metrics JSON,
                
                PRIMARY KEY (conversation_id, turn_number),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Message metrics table (two rows per turn, one per agent)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_metrics (
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                message_index INTEGER NOT NULL,  -- 0 for first speaker, 1 for second
                speaker TEXT NOT NULL CHECK (speaker IN ('agent_a', 'agent_b')),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Message content
                message TEXT NOT NULL,
                
                -- Basic metrics
                message_length INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                sentence_count INTEGER NOT NULL,
                paragraph_count INTEGER DEFAULT 1,
                
                -- Lexical diversity metrics
                vocabulary_size INTEGER NOT NULL,
                type_token_ratio REAL NOT NULL,
                hapax_legomena_count INTEGER NOT NULL,
                hapax_ratio REAL NOT NULL,
                lexical_diversity_index REAL,
                compression_ratio REAL,
                
                -- Linguistic markers
                question_count INTEGER DEFAULT 0,
                exclamation_count INTEGER DEFAULT 0,
                hedge_count INTEGER DEFAULT 0,
                agreement_marker_count INTEGER DEFAULT 0,
                disagreement_marker_count INTEGER DEFAULT 0,
                politeness_marker_count INTEGER DEFAULT 0,
                
                -- Symbol usage
                emoji_count INTEGER DEFAULT 0,
                emoji_density REAL DEFAULT 0.0,
                arrow_count INTEGER DEFAULT 0,
                math_symbol_count INTEGER DEFAULT 0,
                other_symbol_count INTEGER DEFAULT 0,
                punctuation_diversity INTEGER DEFAULT 0,
                
                -- Pronoun usage
                first_person_singular_count INTEGER DEFAULT 0,
                first_person_plural_count INTEGER DEFAULT 0,
                second_person_count INTEGER DEFAULT 0,
                
                -- Numeric content
                number_count INTEGER DEFAULT 0,
                proper_noun_count INTEGER DEFAULT 0,
                
                -- Repetition metrics
                repeated_bigrams INTEGER DEFAULT 0,
                repeated_trigrams INTEGER DEFAULT 0,
                self_repetition_score REAL DEFAULT 0.0,
                
                -- Information theory metrics
                word_entropy REAL,
                character_entropy REAL,
                average_sentence_length REAL,
                
                -- Response characteristics
                response_time_ms INTEGER,
                starts_with_acknowledgment BOOLEAN DEFAULT FALSE,
                ends_with_question BOOLEAN DEFAULT FALSE,
                
                -- Vocabulary tracking
                new_words_count INTEGER DEFAULT 0,
                new_words_ratio REAL DEFAULT 0.0,
                
                -- Enrichable fields (NULL until enriched)
                perplexity REAL,
                sentiment_score REAL,
                formality_score REAL,
                
                -- Additional metrics as JSON
                additional_metrics JSON,
                
                PRIMARY KEY (conversation_id, turn_number, message_index),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Word frequencies table remains the same
        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_frequencies (
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                speaker TEXT NOT NULL CHECK (speaker IN ('agent_a', 'agent_b')),
                word TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                is_new_word BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (conversation_id, turn_number, speaker, word),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Agent names table remains the same
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_names (
                conversation_id TEXT NOT NULL,
                agent_id TEXT NOT NULL CHECK (agent_id IN ('agent_a', 'agent_b')),
                chosen_name TEXT NOT NULL,
                turn_chosen INTEGER NOT NULL,
                name_length INTEGER NOT NULL,
                contains_numbers BOOLEAN DEFAULT FALSE,
                contains_symbols BOOLEAN DEFAULT FALSE,
                contains_spaces BOOLEAN DEFAULT FALSE,
                is_single_word BOOLEAN DEFAULT TRUE,
                starts_with_capital BOOLEAN DEFAULT FALSE,
                all_caps BOOLEAN DEFAULT FALSE,
                metadata JSON,
                PRIMARY KEY (conversation_id, agent_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_experiment ON conversations(experiment_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_metrics_conversation ON turn_metrics(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_message_metrics_conversation ON message_metrics(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_message_metrics_speaker ON message_metrics(conversation_id, speaker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_word_frequencies_conversation ON word_frequencies(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_names_model ON conversations(agent_a_model, agent_b_model)")
        
        # Create views
        conn.execute("""
            CREATE VIEW IF NOT EXISTS experiment_summary AS
            SELECT 
                e.experiment_id,
                e.name,
                e.status,
                e.total_conversations,
                e.completed_conversations,
                e.failed_conversations,
                e.created_at,
                e.completed_at,
                COUNT(DISTINCT c.conversation_id) as actual_conversations,
                AVG(c.total_turns) as avg_turns,
                AVG(c.final_convergence_score) as avg_convergence
            FROM experiments e
            LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
            GROUP BY e.experiment_id
        """)
        
        conn.execute("""
            CREATE VIEW IF NOT EXISTS name_statistics AS
            SELECT 
                c.agent_a_model as model,
                'agent_a' as role,
                n.chosen_name,
                n.name_length,
                n.contains_numbers,
                n.contains_symbols,
                COUNT(*) OVER (PARTITION BY c.agent_a_model, n.chosen_name) as name_frequency
            FROM conversations c
            JOIN agent_names n ON c.conversation_id = n.conversation_id AND n.agent_id = 'agent_a'
            UNION ALL
            SELECT 
                c.agent_b_model as model,
                'agent_b' as role,
                n.chosen_name,
                n.name_length,
                n.contains_numbers,
                n.contains_symbols,
                COUNT(*) OVER (PARTITION BY c.agent_b_model, n.chosen_name) as name_frequency
            FROM conversations c
            JOIN agent_names n ON c.conversation_id = n.conversation_id AND n.agent_id = 'agent_b'
        """)
        
        conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
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
    
    def log_turn_metrics(self, conversation_id: str, turn_number: int, metrics: dict):
        """Log turn-level metrics (convergence, aggregates).
        
        Args:
            conversation_id: Conversation identifier
            turn_number: 0-indexed turn number
            metrics: Dictionary of turn-level metrics
        """
        # Extract turn-level fields
        turn_fields = {
            'convergence_score', 'vocabulary_overlap', 'length_ratio', 
            'structural_similarity', 'cross_repetition_score', 'mimicry_score',
            'total_words', 'total_sentences', 'combined_vocabulary_size',
            'turn_duration_ms', 'agent_a_response_time_ms', 'agent_b_response_time_ms'
        }
        
        # Separate known and additional metrics
        turn_data = {k: metrics.get(k) for k in turn_fields if k in metrics}
        additional = {k: v for k, v in metrics.items() if k not in turn_fields}
        
        # Add required fields
        turn_data['conversation_id'] = conversation_id
        turn_data['turn_number'] = turn_number
        if additional:
            turn_data['additional_metrics'] = json.dumps(additional)
        
        # Build INSERT query dynamically
        fields = list(turn_data.keys())
        placeholders = ['?' for _ in fields]
        
        with self._get_connection() as conn:
            query = f"""
                INSERT INTO turn_metrics ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """
            conn.execute(query, list(turn_data.values()))
            
            # Update conversation turn count
            conn.execute("""
                UPDATE conversations 
                SET total_turns = (
                    SELECT COUNT(DISTINCT turn_number) 
                    FROM turn_metrics 
                    WHERE conversation_id = ?
                )
                WHERE conversation_id = ?
            """, (conversation_id, conversation_id))
            
            conn.commit()
    
    def log_message_metrics(self, conversation_id: str, message_index: int,
                           turn_number: int, speaker: str, metrics: dict):
        """Log message-level metrics.
        
        Args:
            conversation_id: Conversation identifier
            message_index: 0 for first speaker, 1 for second
            turn_number: 0-indexed turn number
            speaker: 'agent_a' or 'agent_b'
            metrics: Dictionary of message metrics
        """
        # Extract message-level fields
        message_fields = {
            'message', 'message_length', 'word_count', 'sentence_count', 'paragraph_count',
            'vocabulary_size', 'type_token_ratio', 'hapax_legomena_count', 'hapax_ratio',
            'lexical_diversity_index', 'compression_ratio',
            'question_count', 'exclamation_count', 'hedge_count', 'agreement_marker_count',
            'disagreement_marker_count', 'politeness_marker_count',
            'emoji_count', 'emoji_density', 'arrow_count', 'math_symbol_count', 
            'other_symbol_count', 'punctuation_diversity',
            'first_person_singular_count', 'first_person_plural_count', 'second_person_count',
            'number_count', 'proper_noun_count',
            'repeated_bigrams', 'repeated_trigrams', 'self_repetition_score',
            'word_entropy', 'character_entropy', 'average_sentence_length',
            'response_time_ms', 'starts_with_acknowledgment', 'ends_with_question',
            'new_words_count', 'new_words_ratio',
            'perplexity', 'sentiment_score', 'formality_score'
        }
        
        # Separate known and additional metrics
        message_data = {k: metrics.get(k) for k in message_fields if k in metrics}
        additional = {k: v for k, v in metrics.items() if k not in message_fields}
        
        # Add required fields
        message_data['conversation_id'] = conversation_id
        message_data['turn_number'] = turn_number
        message_data['message_index'] = message_index
        message_data['speaker'] = speaker
        if additional:
            message_data['additional_metrics'] = json.dumps(additional)
        
        # Build INSERT query dynamically
        fields = list(message_data.keys())
        placeholders = ['?' for _ in fields]
        
        with self._get_connection() as conn:
            query = f"""
                INSERT INTO message_metrics ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """
            conn.execute(query, list(message_data.values()))
            conn.commit()
    
    def log_word_frequencies(self, conversation_id: str, turn_number: int, 
                           speaker: str, word_freq: Dict[str, int], 
                           new_words: Optional[set] = None):
        """Log word frequencies for a turn.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: 0-indexed turn number
            speaker: 'agent_a' or 'agent_b'
            word_freq: Dictionary of word -> frequency
            new_words: Set of words appearing for first time
        """
        new_words = new_words or set()
        
        with self._get_connection() as conn:
            for word, freq in word_freq.items():
                conn.execute("""
                    INSERT INTO word_frequencies (
                        conversation_id, turn_number, speaker, word, frequency, is_new_word
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id, turn_number, speaker, word, freq,
                    word in new_words
                ))
            conn.commit()
    
    def log_agent_name(self, conversation_id: str, agent_id: str, 
                      chosen_name: str, turn_number: int):
        """Log an agent's chosen name.
        
        Args:
            conversation_id: Conversation identifier
            agent_id: 'agent_a' or 'agent_b'
            chosen_name: The name chosen by the agent
            turn_number: Turn when name was chosen
        """
        # Calculate name characteristics
        name_length = len(chosen_name)
        contains_numbers = any(c.isdigit() for c in chosen_name)
        contains_symbols = any(not c.isalnum() and not c.isspace() for c in chosen_name)
        contains_spaces = ' ' in chosen_name
        is_single_word = ' ' not in chosen_name.strip()
        starts_with_capital = chosen_name[0].isupper() if chosen_name else False
        all_caps = chosen_name.isupper()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO agent_names (
                    conversation_id, agent_id, chosen_name, turn_chosen,
                    name_length, contains_numbers, contains_symbols,
                    contains_spaces, is_single_word, starts_with_capital, all_caps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, agent_id, chosen_name, turn_number,
                name_length, contains_numbers, contains_symbols,
                contains_spaces, is_single_word, starts_with_capital, all_caps
            ))
            
            # Also update conversation table
            if agent_id == 'agent_a':
                conn.execute("""
                    UPDATE conversations 
                    SET agent_a_chosen_name = ? 
                    WHERE conversation_id = ?
                """, (chosen_name, conversation_id))
            else:
                conn.execute("""
                    UPDATE conversations 
                    SET agent_b_chosen_name = ? 
                    WHERE conversation_id = ?
                """, (chosen_name, conversation_id))
            
            conn.commit()
    
    def update_conversation_status(self, conversation_id: str, status: str,
                                 convergence_reason: Optional[str] = None,
                                 final_convergence_score: Optional[float] = None,
                                 error_message: Optional[str] = None):
        """Update conversation status and completion details.
        
        Args:
            conversation_id: Conversation identifier
            status: New status ('running', 'completed', 'failed', 'interrupted')
            convergence_reason: Why conversation ended (if completed)
            final_convergence_score: Final convergence score (if completed)
            error_message: Error details (if failed)
        """
        updates = ["status = ?"]
        params = [status]
        
        if status == 'running' and 'started_at' not in params:
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in ('completed', 'failed', 'interrupted'):
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if convergence_reason is not None:
            updates.append("convergence_reason = ?")
            params.append(convergence_reason)
        
        if final_convergence_score is not None:
            updates.append("final_convergence_score = ?")
            params.append(final_convergence_score)
        
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        params.append(conversation_id)
        
        with self._get_connection() as conn:
            conn.execute(f"""
                UPDATE conversations 
                SET {', '.join(updates)}
                WHERE conversation_id = ?
            """, params)
            
            # Update experiment counters
            if status == 'completed':
                conn.execute("""
                    UPDATE experiments 
                    SET completed_conversations = completed_conversations + 1
                    WHERE experiment_id = (
                        SELECT experiment_id FROM conversations 
                        WHERE conversation_id = ?
                    )
                """, (conversation_id,))
            elif status == 'failed':
                conn.execute("""
                    UPDATE experiments 
                    SET failed_conversations = failed_conversations + 1
                    WHERE experiment_id = (
                        SELECT experiment_id FROM conversations 
                        WHERE conversation_id = ?
                    )
                """, (conversation_id,))
            
            conn.commit()
    
    def update_experiment_status(self, experiment_id: str, status: str):
        """Update experiment status.
        
        Args:
            experiment_id: Experiment identifier
            status: New status ('running', 'completed', 'failed')
        """
        updates = ["status = ?"]
        params = [status]
        
        if status == 'running':
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in ('completed', 'failed'):
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        params.append(experiment_id)
        
        with self._get_connection() as conn:
            conn.execute(f"""
                UPDATE experiments 
                SET {', '.join(updates)}
                WHERE experiment_id = ?
            """, params)
            conn.commit()
    
    def get_experiment_status(self, experiment_id: str) -> dict:
        """Get current status of an experiment.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Dictionary with experiment status and progress
        """
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM experiment_summary 
                WHERE experiment_id = ?
            """, (experiment_id,)).fetchone()
            
            if row:
                return dict(row)
            return {}
    
    def get_name_statistics(self, model: Optional[str] = None) -> dict:
        """Get statistics about chosen names.
        
        Args:
            model: Optional model name to filter by
            
        Returns:
            Dictionary with name statistics
        """
        with self._get_connection() as conn:
            if model:
                query = """
                    SELECT * FROM name_statistics 
                    WHERE model = ?
                    ORDER BY name_frequency DESC, chosen_name
                """
                rows = conn.execute(query, (model,)).fetchall()
            else:
                query = """
                    SELECT * FROM name_statistics 
                    ORDER BY model, name_frequency DESC, chosen_name
                """
                rows = conn.execute(query).fetchall()
            
            # Group by model
            stats = {}
            for row in rows:
                model_name = row['model']
                if model_name not in stats:
                    stats[model_name] = []
                stats[model_name].append(dict(row))
            
            return stats
    
    def get_conversations(self, experiment_id: str, 
                         status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversations for an experiment.
        
        Args:
            experiment_id: Experiment identifier
            status: Optional status filter
            
        Returns:
            List of conversation records
        """
        with self._get_connection() as conn:
            if status:
                query = """
                    SELECT * FROM conversations 
                    WHERE experiment_id = ? AND status = ?
                    ORDER BY created_at
                """
                rows = conn.execute(query, (experiment_id, status)).fetchall()
            else:
                query = """
                    SELECT * FROM conversations 
                    WHERE experiment_id = ?
                    ORDER BY created_at
                """
                rows = conn.execute(query, (experiment_id,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def list_experiments(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List experiments with summary information.
        
        Args:
            limit: Maximum number of experiments to return
            offset: Number of experiments to skip
            
        Returns:
            List of experiment dictionaries with summary info
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    e.experiment_id,
                    e.name,
                    e.status,
                    e.created_at,
                    e.started_at,
                    e.completed_at,
                    e.total_conversations,
                    e.completed_conversations,
                    e.failed_conversations,
                    json_extract(e.config, '$.agent_a_model') as agent_a_model,
                    json_extract(e.config, '$.agent_b_model') as agent_b_model,
                    json_extract(e.config, '$.max_turns') as max_turns,
                    json_extract(e.config, '$.repetitions') as repetitions
                FROM experiments e
                ORDER BY e.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, (limit, offset)).fetchall()
            
            experiments = []
            for row in rows:
                exp = dict(row)
                # Parse JSON config for convenience
                if 'config' in exp and exp['config']:
                    try:
                        exp['config'] = json.loads(exp['config'])
                    except:
                        pass
                experiments.append(exp)
                
            return experiments
    
    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get experiment by name.
        
        Args:
            name: Experiment name to search for
            
        Returns:
            Experiment dictionary or None if not found
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    e.experiment_id,
                    e.name,
                    e.status,
                    e.created_at,
                    e.started_at,
                    e.completed_at,
                    e.total_conversations,
                    e.completed_conversations,
                    e.failed_conversations,
                    e.config,
                    json_extract(e.config, '$.agent_a_model') as agent_a_model,
                    json_extract(e.config, '$.agent_b_model') as agent_b_model,
                    json_extract(e.config, '$.dashboard_attached') as dashboard_attached
                FROM experiments e
                WHERE e.name = ?
                ORDER BY e.created_at DESC
                LIMIT 1
            """
            row = conn.execute(query, (name,)).fetchone()
            
            if row:
                exp = dict(row)
                # Parse JSON config
                if 'config' in exp and exp['config']:
                    try:
                        exp['config'] = json.loads(exp['config'])
                        # Extract dashboard_attached from config
                        exp['dashboard_attached'] = exp['config'].get('dashboard_attached', False)
                    except:
                        exp['dashboard_attached'] = False
                return exp
            return None
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details by ID.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Experiment dictionary or None if not found
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    e.*,
                    json_extract(e.config, '$.agent_a_model') as agent_a_model,
                    json_extract(e.config, '$.agent_b_model') as agent_b_model
                FROM experiments e
                WHERE e.experiment_id = ?
            """
            row = conn.execute(query, (experiment_id,)).fetchone()
            
            if row:
                exp = dict(row)
                # Parse JSON config
                if 'config' in exp and exp['config']:
                    try:
                        exp['config'] = json.loads(exp['config'])
                    except:
                        pass
                return exp
            return None
    
    def update_dashboard_attachment(self, experiment_id: str, attached: bool) -> None:
        """Update dashboard attachment status.
        
        Args:
            experiment_id: Experiment ID
            attached: Whether dashboard is attached
        """
        with self._get_connection() as conn:
            # First get current config
            config_json = conn.execute(
                "SELECT config FROM experiments WHERE experiment_id = ?",
                (experiment_id,)
            ).fetchone()
            
            if config_json and config_json['config']:
                try:
                    config = json.loads(config_json['config'])
                except:
                    config = {}
            else:
                config = {}
            
            # Update dashboard_attached in config
            config['dashboard_attached'] = attached
            
            # Save back to database
            conn.execute("""
                UPDATE experiments 
                SET config = ?
                WHERE experiment_id = ?
            """, (json.dumps(config), experiment_id))
            conn.commit()
    
    def get_turn_metrics(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get turn-level metrics for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of turn metric dictionaries
        """
        with self._get_connection() as conn:
            query = """
                SELECT * FROM turn_metrics 
                WHERE conversation_id = ?
                ORDER BY turn_number
            """
            rows = conn.execute(query, (conversation_id,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_message_metrics(self, conversation_id: str, 
                          speaker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get message-level metrics for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            speaker: Optional filter by speaker
            
        Returns:
            List of message metric dictionaries
        """
        with self._get_connection() as conn:
            if speaker:
                query = """
                    SELECT * FROM message_metrics 
                    WHERE conversation_id = ? AND speaker = ?
                    ORDER BY turn_number, message_index
                """
                rows = conn.execute(query, (conversation_id, speaker)).fetchall()
            else:
                query = """
                    SELECT * FROM message_metrics 
                    WHERE conversation_id = ?
                    ORDER BY turn_number, message_index
                """
                rows = conn.execute(query, (conversation_id,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_high_convergence_turns(self, experiment_id: str, 
                                 threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Get turns with high convergence scores.
        
        Args:
            experiment_id: Experiment identifier
            threshold: Minimum convergence score
            
        Returns:
            List of high convergence turn records
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    t.conversation_id,
                    t.turn_number,
                    t.convergence_score,
                    t.vocabulary_overlap,
                    t.structural_similarity,
                    m1.message as agent_a_message,
                    m2.message as agent_b_message
                FROM turn_metrics t
                JOIN message_metrics m1 ON t.conversation_id = m1.conversation_id 
                    AND t.turn_number = m1.turn_number AND m1.speaker = 'agent_a'
                JOIN message_metrics m2 ON t.conversation_id = m2.conversation_id 
                    AND t.turn_number = m2.turn_number AND m2.speaker = 'agent_b'
                WHERE t.conversation_id IN (
                    SELECT conversation_id FROM conversations 
                    WHERE experiment_id = ?
                ) AND t.convergence_score >= ?
                ORDER BY t.convergence_score DESC
            """
            rows = conn.execute(query, (experiment_id, threshold)).fetchall()
            return [dict(row) for row in rows]
    
    def get_vocabulary_evolution(self, conversation_id: str) -> Dict[str, Any]:
        """Get vocabulary evolution metrics over time.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Dictionary with vocabulary evolution data
        """
        with self._get_connection() as conn:
            # Get vocabulary size over turns
            query = """
                SELECT 
                    turn_number,
                    SUM(vocabulary_size) as combined_vocabulary,
                    AVG(type_token_ratio) as avg_ttr,
                    AVG(lexical_diversity_index) as avg_ldi
                FROM message_metrics
                WHERE conversation_id = ?
                GROUP BY turn_number
                ORDER BY turn_number
            """
            vocab_rows = conn.execute(query, (conversation_id,)).fetchall()
            
            # Get new words introduced per turn
            query = """
                SELECT 
                    turn_number,
                    speaker,
                    COUNT(DISTINCT word) as new_words_introduced
                FROM word_frequencies
                WHERE conversation_id = ? AND is_new_word = 1
                GROUP BY turn_number, speaker
                ORDER BY turn_number, speaker
            """
            new_words_rows = conn.execute(query, (conversation_id,)).fetchall()
            
            return {
                'vocabulary_by_turn': [dict(row) for row in vocab_rows],
                'new_words_by_turn': [dict(row) for row in new_words_rows]
            }
    
    def get_active_conversations(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get active conversations for dashboard display.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            List of active conversation dictionaries with metrics
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    c.conversation_id,
                    c.status,
                    c.agent_a_model,
                    c.agent_b_model,
                    c.total_turns as turn_number,
                    json_extract(c.config, '$.max_turns') as max_turns,
                    c.started_at,
                    tm.vocabulary_overlap,
                    tm.convergence_score,
                    CASE 
                        WHEN (julianday('now') - julianday(mm.timestamp)) * 86400 < 60 
                        THEN 0
                        ELSE 1
                    END as rate_limited,
                    (julianday('now') - julianday(mm.timestamp)) * 86400 as rate_limit_wait
                FROM conversations c
                LEFT JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
                    AND tm.turn_number = (
                        SELECT MAX(turn_number) FROM turn_metrics 
                        WHERE conversation_id = c.conversation_id
                    )
                LEFT JOIN message_metrics mm ON c.conversation_id = mm.conversation_id
                    AND mm.turn_number = (
                        SELECT MAX(turn_number) FROM message_metrics
                        WHERE conversation_id = c.conversation_id
                    )
                WHERE c.experiment_id = ? 
                    AND c.status IN ('running', 'created')
                ORDER BY c.started_at DESC
            """
            rows = conn.execute(query, (experiment_id,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_active_conversation_count(self, experiment_id: str) -> int:
        """Get count of active conversations.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Number of active conversations
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT COUNT(*) as count
                FROM conversations 
                WHERE experiment_id = ? AND status = 'running'
            """, (experiment_id,)).fetchone()
            return result['count'] if result else 0
    
    def get_latest_turn_metrics(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get most recent turn metrics for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Latest turn metrics or None
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    tm.*,
                    AVG(mm.message_length) as avg_message_length
                FROM turn_metrics tm
                LEFT JOIN message_metrics mm ON tm.conversation_id = mm.conversation_id
                    AND tm.turn_number = mm.turn_number
                WHERE tm.conversation_id = ?
                GROUP BY tm.conversation_id, tm.turn_number
                ORDER BY tm.turn_number DESC
                LIMIT 1
            """
            row = conn.execute(query, (conversation_id,)).fetchone()
            return dict(row) if row else None
    
    def get_last_message(self, conversation_id: str) -> Optional[str]:
        """Get the last message from a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Last message text or None
        """
        with self._get_connection() as conn:
            query = """
                SELECT message 
                FROM message_metrics
                WHERE conversation_id = ?
                ORDER BY turn_number DESC, message_index DESC
                LIMIT 1
            """
            row = conn.execute(query, (conversation_id,)).fetchone()
            return row['message'] if row else None
    
    def calculate_experiment_statistics(self, experiment_id: str) -> Dict[str, Any]:
        """Calculate comprehensive statistics for experiment dashboard.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Dictionary with various statistical distributions
        """
        with self._get_connection() as conn:
            # Vocabulary overlap distribution
            overlap_query = """
                SELECT 
                    CASE
                        WHEN vocabulary_overlap < 0.2 THEN '0_20'
                        WHEN vocabulary_overlap < 0.4 THEN '20_40'
                        WHEN vocabulary_overlap < 0.6 THEN '40_60'
                        WHEN vocabulary_overlap < 0.8 THEN '60_80'
                        ELSE '80_100'
                    END as bucket,
                    COUNT(*) as count
                FROM turn_metrics
                WHERE conversation_id IN (
                    SELECT conversation_id FROM conversations 
                    WHERE experiment_id = ?
                )
                GROUP BY bucket
            """
            overlap_rows = conn.execute(overlap_query, (experiment_id,)).fetchall()
            overlap_dist = {row['bucket']: row['count'] for row in overlap_rows}
            
            # Message length distribution
            length_query = """
                SELECT 
                    CASE
                        WHEN message_length < 50 THEN 'under_50'
                        WHEN message_length < 100 THEN '50_100'
                        WHEN message_length < 150 THEN '100_150'
                        ELSE 'over_150'
                    END as bucket,
                    COUNT(*) as count
                FROM message_metrics
                WHERE conversation_id IN (
                    SELECT conversation_id FROM conversations 
                    WHERE experiment_id = ?
                )
                GROUP BY bucket
            """
            length_rows = conn.execute(length_query, (experiment_id,)).fetchall()
            length_dist = {row['bucket']: row['count'] for row in length_rows}
            
            # Word frequency evolution
            early_words_query = """
                SELECT word, SUM(frequency) as total_freq
                FROM word_frequencies
                WHERE conversation_id IN (
                    SELECT conversation_id FROM conversations 
                    WHERE experiment_id = ?
                ) AND turn_number BETWEEN 0 AND 9
                GROUP BY word
                ORDER BY total_freq DESC
                LIMIT 10
            """
            early_rows = conn.execute(early_words_query, (experiment_id,)).fetchall()
            early_words = [row['word'] for row in early_rows]
            
            late_words_query = """
                SELECT word, SUM(frequency) as total_freq
                FROM word_frequencies
                WHERE conversation_id IN (
                    SELECT conversation_id FROM conversations 
                    WHERE experiment_id = ?
                ) AND turn_number BETWEEN 40 AND 49
                GROUP BY word
                ORDER BY total_freq DESC
                LIMIT 10
            """
            late_rows = conn.execute(late_words_query, (experiment_id,)).fetchall()
            late_words = [row['word'] for row in late_rows]
            
            # Word frequency changes
            freq_changes_query = """
                WITH early_freq AS (
                    SELECT word, SUM(frequency) as early_count
                    FROM word_frequencies
                    WHERE conversation_id IN (
                        SELECT conversation_id FROM conversations 
                        WHERE experiment_id = ?
                    ) AND turn_number < 10
                    GROUP BY word
                ),
                late_freq AS (
                    SELECT word, SUM(frequency) as late_count
                    FROM word_frequencies
                    WHERE conversation_id IN (
                        SELECT conversation_id FROM conversations 
                        WHERE experiment_id = ?
                    ) AND turn_number >= 40
                    GROUP BY word
                )
                SELECT 
                    COALESCE(e.word, l.word) as word,
                    COALESCE(e.early_count, 0) as start_count,
                    COALESCE(l.late_count, 0) as end_count,
                    ABS(COALESCE(l.late_count, 0) - COALESCE(e.early_count, 0)) as change
                FROM early_freq e
                FULL OUTER JOIN late_freq l ON e.word = l.word
                ORDER BY change DESC
                LIMIT 10
            """
            # SQLite doesn't support FULL OUTER JOIN, so we use UNION
            freq_changes_query = """
                SELECT word, early_count as start_count, late_count as end_count
                FROM (
                    SELECT 
                        word,
                        SUM(CASE WHEN turn_number < 10 THEN frequency ELSE 0 END) as early_count,
                        SUM(CASE WHEN turn_number >= 40 THEN frequency ELSE 0 END) as late_count
                    FROM word_frequencies
                    WHERE conversation_id IN (
                        SELECT conversation_id FROM conversations 
                        WHERE experiment_id = ?
                    )
                    GROUP BY word
                    HAVING (late_count - early_count) != 0
                    ORDER BY ABS(late_count - early_count) DESC
                    LIMIT 10
                )
            """
            change_rows = conn.execute(freq_changes_query, (experiment_id,)).fetchall()
            top_changes = [(row['word'], (row['start_count'], row['end_count'])) 
                          for row in change_rows]
            
            # Temperature effects if applicable
            temp_query = """
                SELECT 
                    json_extract(c.config, '$.temperature_a') as temperature,
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
                'overlap_distribution': overlap_dist,
                'length_distribution': length_dist,
                'word_frequency_changes': {
                    'early_words': early_words,
                    'late_words': late_words,
                    'top_changes': top_changes
                },
                'temperature_effects': temp_effects
            }
    
    def stop_experiment(self, experiment_id: str):
        """Stop an experiment by updating its status.
        
        Args:
            experiment_id: Experiment identifier
        """
        self.update_experiment_status(experiment_id, 'completed')