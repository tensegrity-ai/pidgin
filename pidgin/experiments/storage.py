"""Storage layer for Pidgin experiments using SQLite."""

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
            db_path = Path("./pidgin_output/experiments/experiments.db").resolve()
        
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Load and execute schema
            with open(schema_path) as f:
                conn.executescript(f.read())
    
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
        """Log metrics for a conversation turn.
        
        Args:
            conversation_id: Conversation identifier
            turn_number: 0-indexed turn number
            metrics: Dictionary of all turn metrics
        """
        # Extract known fields
        known_fields = {
            'speaker', 'message', 'message_length', 'word_count', 'sentence_count',
            'vocabulary_size', 'type_token_ratio', 'hapax_legomena_count', 'hapax_ratio',
            'convergence_score', 'vocabulary_overlap', 'length_ratio', 'structural_similarity',
            'question_count', 'exclamation_count', 'hedge_count', 'agreement_marker_count',
            'disagreement_marker_count', 'politeness_marker_count', 'emoji_count',
            'emoji_density', 'arrow_count', 'math_symbol_count', 'other_symbol_count',
            'first_person_singular_count', 'first_person_plural_count', 'second_person_count',
            'repeated_bigrams', 'repeated_trigrams', 'self_repetition_score',
            'cross_repetition_score', 'word_entropy', 'character_entropy', 'perplexity',
            'sentiment_score', 'formality_score', 'response_time_ms',
            'starts_with_acknowledgment', 'ends_with_question'
        }
        
        # Separate known and additional metrics
        turn_data = {k: metrics.get(k) for k in known_fields if k in metrics}
        additional = {k: v for k, v in metrics.items() if k not in known_fields}
        
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
                INSERT INTO turns ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """
            conn.execute(query, list(turn_data.values()))
            
            # Update conversation turn count
            conn.execute("""
                UPDATE conversations 
                SET total_turns = (
                    SELECT COUNT(DISTINCT turn_number) 
                    FROM turns 
                    WHERE conversation_id = ?
                )
                WHERE conversation_id = ?
            """, (conversation_id, conversation_id))
            
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