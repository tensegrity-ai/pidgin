"""Service for importing JSONL experiment data into the database."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import duckdb

from .event_repository import EventRepository
from .experiment_repository import ExperimentRepository
from .conversation_repository import ConversationRepository
from .message_repository import MessageRepository
from .metrics_repository import MetricsRepository
from .event_replay import EventReplay
from ..io.logger import get_logger
from ..metrics.calculator import MetricsCalculator

logger = get_logger("import_service")


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    experiment_id: str
    events_imported: int
    conversations_imported: int
    error: Optional[str] = None
    duration_seconds: float = 0.0


class ImportService:
    """Service for importing JSONL experiment data into DuckDB.
    
    Handles the batch import of experiment data from JSONL files into
    the database after experiments complete.
    """
    
    def __init__(self, 
                 db: duckdb.DuckDBPyConnection,
                 events: EventRepository,
                 experiments: ExperimentRepository,
                 conversations: ConversationRepository,
                 messages: MessageRepository,
                 metrics: MetricsRepository):
        """Initialize with database connection and repositories.
        
        Args:
            db: DuckDB connection
            events: Event repository
            experiments: Experiment repository
            conversations: Conversation repository
            messages: Message repository
            metrics: Metrics repository
        """
        self.db = db
        self.events = events
        self.experiments = experiments
        self.conversations = conversations
        self.messages = messages
        self.metrics = metrics
        self.metrics_calculator = MetricsCalculator()
    
    def _check_import_status(self, exp_dir: Path, imported_marker: Path, 
                            importing_marker: Path) -> Optional[ImportResult]:
        """Check if experiment is already imported or being imported.
        
        Returns:
            ImportResult if already handled, None if ready to import
        """
        if imported_marker.exists():
            logger.info(f"Experiment {exp_dir.name} already imported")
            return ImportResult(
                success=True,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                error="Already imported"
            )
        
        if importing_marker.exists():
            logger.warning(f"Import already in progress for {exp_dir.name}")
            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                error="Import in progress"
            )
        
        return None
    
    def _load_manifest(self, manifest_path: Path) -> Optional[Dict[str, Any]]:
        """Load and validate manifest file.
        
        Returns:
            Manifest data or None if not found
        """
        if not manifest_path.exists():
            return None
        
        with open(manifest_path) as f:
            return json.load(f)
    
    def _import_experiment_data(self, exp_dir: Path, manifest_data: Dict[str, Any]) -> tuple[int, int]:
        """Import experiment and conversation data within a transaction.
        
        Returns:
            Tuple of (events_count, conversations_count)
        """
        experiment_id = manifest_data.get("experiment_id", exp_dir.name)
        
        # Import experiment record
        self._import_experiment_record(manifest_data)
        
        # Import conversations and events
        events_count = 0
        conversations_count = 0
        
        for conv_id, conv_info in manifest_data.get("conversations", {}).items():
            jsonl_path = exp_dir / conv_info["jsonl"]
            if jsonl_path.exists():
                event_count = self._import_conversation_from_jsonl(
                    experiment_id, conv_id, jsonl_path
                )
                events_count += event_count
                conversations_count += 1
        
        return events_count, conversations_count
    
    def _create_import_marker(self, imported_marker: Path, events_count: int, 
                            conversations_count: int) -> None:
        """Create marker file indicating successful import."""
        with open(imported_marker, 'w') as f:
            json.dump({
                "imported_at": datetime.now().isoformat(),
                "events_count": events_count,
                "conversations_count": conversations_count
            }, f)
    
    def _enhance_error_message(self, error_msg: str) -> str:
        """Create more descriptive error messages for common database errors."""
        if "binder error" in error_msg.lower() and "does not have a column" in error_msg.lower():
            # Extract column name from error
            import re
            match = re.search(r'"(\w+)" does not have a column with name "(\w+)"', error_msg)
            if match:
                table_name, column_name = match.groups()
                return f"Database schema mismatch: Table '{table_name}' is missing column '{column_name}'. The database schema may need to be updated."
        elif "no such table" in error_msg.lower():
            return f"Database not initialized properly: {error_msg}"
        
        return error_msg
    
    def _batch_insert_events(self, events: List[tuple], experiment_id: str, conversation_id: str) -> None:
        """Batch insert events for better performance.
        
        Args:
            events: List of (line_num, event) tuples
            experiment_id: Experiment ID
            conversation_id: Conversation ID
        """
        if not events:
            return
        
        # Prepare batch data
        batch_data = []
        for line_num, event in events:
            # Serialize event back to JSON for storage
            event_data = {
                "event_type": event.__class__.__name__,
                "timestamp": event.timestamp.isoformat(),
                "event_id": event.event_id,
                "conversation_id": conversation_id,
                # Add event-specific fields
                **{k: v for k, v in event.__dict__.items() 
                   if k not in ["timestamp", "event_id"]}
            }
            
            batch_data.append([
                event.timestamp.isoformat(),
                event.__class__.__name__,
                conversation_id,
                experiment_id,
                json.dumps(event_data, default=str),
                line_num
            ])
        
        # Execute batch insert using DuckDB's executemany for better performance
        query = """
            INSERT INTO events (
                timestamp, event_type, conversation_id, 
                experiment_id, event_data, sequence
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        self.db.executemany(query, batch_data)
        logger.debug(f"Batch inserted {len(batch_data)} events for conversation {conversation_id}")
    
    def _batch_insert_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Batch insert messages for better performance.
        
        Args:
            messages: List of message dictionaries
        """
        if not messages:
            return
        
        # Prepare batch data
        batch_data = []
        for msg in messages:
            batch_data.append([
                msg["conversation_id"],
                msg["turn_number"],
                msg["agent_id"],
                msg["content"],
                msg["timestamp"].isoformat() if isinstance(msg["timestamp"], datetime) else msg["timestamp"],
                msg["token_count"]
            ])
        
        # Execute batch insert
        query = """
            INSERT INTO messages (
                conversation_id, turn_number, agent_id, 
                content, timestamp, token_count
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        self.db.executemany(query, batch_data)
        logger.debug(f"Batch inserted {len(batch_data)} messages")

    def import_experiment_from_jsonl(self, exp_dir: Path) -> ImportResult:
        """Import experiment data from JSONL files into database.
        
        Args:
            exp_dir: Directory containing manifest.json and JSONL files
            
        Returns:
            ImportResult with success status and counts
        """
        start_time = datetime.now()
        
        # Setup paths
        manifest_path = exp_dir / "manifest.json"
        imported_marker = exp_dir / ".imported"
        importing_marker = exp_dir / ".importing"
        
        try:
            # Check if manifest exists
            manifest_data = self._load_manifest(manifest_path)
            if not manifest_data:
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="No manifest.json found"
                )
            
            # Check import status
            status_result = self._check_import_status(exp_dir, imported_marker, importing_marker)
            if status_result:
                return status_result
            
            # Mark as importing
            importing_marker.touch()
            
            try:
                experiment_id = manifest_data.get("experiment_id", exp_dir.name)
                
                # Begin transaction for the import
                self.db.begin()
                
                # Import all data
                events_count, conversations_count = self._import_experiment_data(
                    exp_dir, manifest_data
                )
                
                # Commit transaction
                self.db.commit()
                
                # Create imported marker
                importing_marker.unlink()
                self._create_import_marker(imported_marker, events_count, conversations_count)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.debug(f"Successfully imported {experiment_id}: "
                           f"{events_count} events, {conversations_count} conversations")
                
                return ImportResult(
                    success=True,
                    experiment_id=experiment_id,
                    events_imported=events_count,
                    conversations_imported=conversations_count,
                    duration_seconds=duration
                )
                
            except Exception as e:
                # Rollback on error
                self.db.rollback()
                
                # Clean up importing marker
                if importing_marker.exists():
                    importing_marker.unlink()
                raise
                
        except Exception as e:
            # Enhance error message
            error_msg = self._enhance_error_message(str(e))
            
            # Log at debug level since the runner will display this nicely
            logger.debug(f"Failed to import {exp_dir.name}: {error_msg}")
            
            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                error=error_msg,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def import_all_pending(self, experiments_dir: Path) -> List[ImportResult]:
        """Import all experiments that have JSONL files but haven't been imported.
        
        Args:
            experiments_dir: Root directory containing experiment subdirectories
            
        Returns:
            List of ImportResults for each experiment
        """
        results = []
        
        if not experiments_dir.exists():
            logger.warning(f"Experiments directory {experiments_dir} does not exist")
            return results
        
        # Find all experiment directories
        for exp_dir in experiments_dir.iterdir():
            if not exp_dir.is_dir() or exp_dir.name.startswith('.'):
                continue
            
            # Check if it has a manifest
            if not (exp_dir / "manifest.json").exists():
                continue
            
            # Import if not already imported
            result = self.import_experiment_from_jsonl(exp_dir)
            results.append(result)
        
        return results
    
    def _import_experiment_record(self, manifest: Dict[str, Any]) -> None:
        """Import experiment metadata from manifest."""
        # Check if experiment already exists
        result = self.db.execute(
            "SELECT COUNT(*) FROM experiments WHERE experiment_id = ?",
            [manifest["experiment_id"]]
        ).fetchone()
        
        if result[0] > 0:
            # Update existing record
            self.db.execute("""
                UPDATE experiments SET
                    status = ?,
                    completed_conversations = ?,
                    failed_conversations = ?,
                    metadata = ?
                WHERE experiment_id = ?
            """, [
                manifest.get("status", "unknown"),
                manifest.get("completed_conversations", 0),
                manifest.get("failed_conversations", 0),
                json.dumps({
                    "manifest_version": "2.0",
                    "imported_at": datetime.now().isoformat()
                }),
                manifest["experiment_id"]
            ])
        else:
            # Insert new record
            self.db.execute("""
                INSERT INTO experiments (
                    experiment_id, name, created_at, started_at, completed_at,
                    status, config, total_conversations, 
                    completed_conversations, failed_conversations, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                manifest["experiment_id"],
                manifest.get("name") or manifest["experiment_id"],
                manifest.get("created_at"),
                manifest.get("started_at"),
                manifest.get("completed_at"),
                manifest.get("status", "unknown"),
                json.dumps(manifest.get("config", {})),
                manifest.get("total_conversations", 0),
                manifest.get("completed_conversations", 0),
                manifest.get("failed_conversations", 0),
                json.dumps({
                    "manifest_version": "2.0",
                    "imported_at": datetime.now().isoformat()
                })
            ])
    
    def _import_conversation_from_jsonl(self, experiment_id: str, 
                                       conversation_id: str,
                                       jsonl_path: Path) -> int:
        """Import a single conversation from JSONL file.
        
        Returns:
            Number of events imported
        """
        # Use EventReplay to reconstruct conversation state
        replayer = EventReplay()
        state = replayer.replay_conversation(experiment_id, conversation_id, jsonl_path)
        
        # Batch insert all events for better performance
        self._batch_insert_events(state.events, experiment_id, conversation_id)
        
        # Create/update conversation record
        if state.started_at:
            # Check if conversation already exists
            result = self.db.execute(
                "SELECT COUNT(*) FROM conversations WHERE conversation_id = ?",
                [conversation_id]
            ).fetchone()
            
            if result[0] > 0:
                # Update existing
                self.db.execute("""
                    UPDATE conversations SET
                        status = ?,
                        completed_at = ?,
                        total_turns = ?,
                        final_convergence_score = ?
                    WHERE conversation_id = ?
                """, [
                    state.status,
                    state.completed_at.isoformat() if state.completed_at else None,
                    state.total_turns,
                    state.final_convergence_score,
                    conversation_id
                ])
            else:
                # Insert new conversation
                self.db.execute("""
                    INSERT INTO conversations (
                        conversation_id, experiment_id, started_at, completed_at,
                        status, agent_a_model, agent_b_model, max_turns, 
                        total_turns, initial_prompt, final_convergence_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    conversation_id,
                    experiment_id,
                    state.started_at.isoformat() if state.started_at else None,
                    state.completed_at.isoformat() if state.completed_at else None,
                    state.status,
                    state.agent_a_model,
                    state.agent_b_model,
                    state.max_turns,
                    state.total_turns,
                    state.initial_prompt,
                    state.final_convergence_score
                ])
        
        # Insert agent names if any were chosen
        for agent_id, name in state.agent_names.items():
            self.conversations.log_agent_name(conversation_id, agent_id, name)
        
        # Batch insert messages for better performance
        self._batch_insert_messages(state.messages)
        
        # Calculate and insert full turn metrics
        self._calculate_and_store_turn_metrics(state)
        
        return len(state.events)
    
    def _calculate_and_store_turn_metrics(self, state) -> None:
        """Calculate and store all metrics for each turn."""
        # Reset calculator for this conversation
        self.metrics_calculator = MetricsCalculator()
        
        for idx, (msg_a, msg_b) in enumerate(state.turns):
            # Get timing info and turn number from existing turn metrics
            existing_metric = state.turn_metrics[idx] if idx < len(state.turn_metrics) else {}
            turn_num = existing_metric.get('turn_number', idx)
            
            # Calculate all metrics
            metrics = self.metrics_calculator.calculate_turn_metrics(
                turn_number=idx,  # Use index for calculator (it expects 0-based)
                agent_a_message=msg_a.content,
                agent_b_message=msg_b.content
            )
            
            # Prepare metric values for insertion
            metric_values = self._prepare_turn_metric_values(
                state.conversation_id, turn_num, existing_metric, metrics, msg_a, msg_b
            )
            
            # Insert metrics using prepared values
            self._insert_turn_metrics(metric_values)
    
    def _prepare_turn_metric_values(self, conversation_id: str, turn_num: int, 
                                    existing_metric: dict, metrics: dict, 
                                    msg_a, msg_b) -> list:
        """Prepare metric values for database insertion."""
        from collections import Counter
        
        # Extract vocabularies
        words_a = metrics['agent_a'].get('vocabulary', set())
        words_b = metrics['agent_b'].get('vocabulary', set())
        
        # Count word frequencies
        word_freq_a = dict(Counter(word for word in msg_a.content.lower().split() if word in words_a))
        word_freq_b = dict(Counter(word for word in msg_b.content.lower().split() if word in words_b))
        shared_vocab = list(words_a.intersection(words_b))
        
        return [
            conversation_id,
            turn_num,
            existing_metric.get('timestamp', datetime.now()),
            # Core convergence
            existing_metric.get('convergence_score', 0.0),  # From live calculation
            metrics['convergence'].get('vocabulary_overlap', 0.0),
            metrics['convergence'].get('structural_similarity', 0.0),
            0.0,  # topic_similarity - not implemented
            0.0,  # style_match - not implemented
            # Additional convergence
            metrics['convergence'].get('cumulative_overlap', 0.0),
            metrics['convergence'].get('cross_repetition', 0.0),
            metrics['convergence'].get('mimicry_a_to_b', 0.0),
            metrics['convergence'].get('mimicry_b_to_a', 0.0),
            metrics['convergence'].get('mutual_mimicry', 0.0),
            # Agent A metrics
            *self._extract_agent_metrics(metrics['agent_a']),
            # Agent B metrics
            *self._extract_agent_metrics(metrics['agent_b']),
            # Word frequencies as JSON
            json.dumps(word_freq_a),
            json.dumps(word_freq_b),
            json.dumps(shared_vocab),
            # Timing information
            None,  # turn_start_time
            None,  # turn_end_time  
            None   # duration_ms
        ]
    
    def _extract_agent_metrics(self, agent_metrics: dict) -> list:
        """Extract agent-specific metrics in the correct order."""
        return [
            agent_metrics['message_length'],
            agent_metrics['word_count'],
            agent_metrics['vocabulary_size'],
            agent_metrics['vocabulary_size'] / max(agent_metrics['word_count'], 1),  # type_token_ratio
            agent_metrics['avg_word_length'],
            0,  # response_time_ms - not available
            agent_metrics['sentence_count'],
            agent_metrics['paragraph_count'],
            agent_metrics['avg_sentence_length'],
            agent_metrics['question_count'],
            agent_metrics['exclamation_count'],
            agent_metrics['special_symbol_count'],
            agent_metrics['number_count'],
            agent_metrics['proper_noun_count'],
            agent_metrics['entropy'],
            agent_metrics['compression_ratio'],
            agent_metrics['lexical_diversity'],
            agent_metrics['punctuation_diversity'],
            agent_metrics['self_repetition'],
            agent_metrics['turn_repetition'],
            agent_metrics['formality_score'],
            agent_metrics['starts_with_acknowledgment'],
            agent_metrics['new_words'],
            # Linguistic markers
            agent_metrics.get('hedge_words', 0),
            agent_metrics.get('agreement_markers', 0),
            agent_metrics.get('disagreement_markers', 0),
            agent_metrics.get('politeness_markers', 0),
            agent_metrics.get('first_person_singular', 0),
            agent_metrics.get('first_person_plural', 0),
            agent_metrics.get('second_person', 0)
        ]
    
    def _insert_turn_metrics(self, values: list) -> None:
        """Execute the turn metrics INSERT statement."""
        self.db.execute("""
            INSERT INTO turn_metrics (
                conversation_id, turn_number, timestamp,
                -- Core convergence metrics
                convergence_score, vocabulary_overlap, structural_similarity,
                topic_similarity, style_match,
                -- Additional convergence metrics
                cumulative_overlap, cross_repetition,
                mimicry_a_to_b, mimicry_b_to_a, mutual_mimicry,
                -- Agent A metrics
                message_a_length, message_a_word_count, message_a_unique_words,
                message_a_type_token_ratio, message_a_avg_word_length,
                message_a_response_time_ms,
                message_a_sentence_count, message_a_paragraph_count,
                message_a_avg_sentence_length,
                message_a_question_count, message_a_exclamation_count,
                message_a_special_symbol_count, message_a_number_count,
                message_a_proper_noun_count,
                message_a_entropy, message_a_compression_ratio,
                message_a_lexical_diversity, message_a_punctuation_diversity,
                message_a_self_repetition, message_a_turn_repetition,
                message_a_formality_score, message_a_starts_with_ack,
                message_a_new_words,
                -- Agent A linguistic markers
                message_a_hedge_words, message_a_agreement_markers,
                message_a_disagreement_markers, message_a_politeness_markers,
                message_a_first_person_singular, message_a_first_person_plural,
                message_a_second_person,
                -- Agent B metrics
                message_b_length, message_b_word_count, message_b_unique_words,
                message_b_type_token_ratio, message_b_avg_word_length,
                message_b_response_time_ms,
                message_b_sentence_count, message_b_paragraph_count,
                message_b_avg_sentence_length,
                message_b_question_count, message_b_exclamation_count,
                message_b_special_symbol_count, message_b_number_count,
                message_b_proper_noun_count,
                message_b_entropy, message_b_compression_ratio,
                message_b_lexical_diversity, message_b_punctuation_diversity,
                message_b_self_repetition, message_b_turn_repetition,
                message_b_formality_score, message_b_starts_with_ack,
                message_b_new_words,
                -- Agent B linguistic markers
                message_b_hedge_words, message_b_agreement_markers,
                message_b_disagreement_markers, message_b_politeness_markers,
                message_b_first_person_singular, message_b_first_person_plural,
                message_b_second_person,
                -- Word frequencies
                word_frequencies_a, word_frequencies_b, shared_vocabulary,
                -- Timing information
                turn_start_time, turn_end_time, duration_ms
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
        """, values)