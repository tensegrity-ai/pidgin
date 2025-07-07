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
    
    def import_experiment_from_jsonl(self, exp_dir: Path) -> ImportResult:
        """Import experiment data from JSONL files into database.
        
        Args:
            exp_dir: Directory containing manifest.json and JSONL files
            
        Returns:
            ImportResult with success status and counts
        """
        start_time = datetime.now()
        
        try:
            # Check for manifest
            manifest_path = exp_dir / "manifest.json"
            if not manifest_path.exists():
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="No manifest.json found"
                )
            
            # Check import status markers
            imported_marker = exp_dir / ".imported"
            importing_marker = exp_dir / ".importing"
            
            if imported_marker.exists():
                logger.info(f"Experiment {exp_dir.name} already imported")
                return ImportResult(
                    success=True,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="Already imported"
                )
            
            # Check if another import is in progress
            if importing_marker.exists():
                logger.warning(f"Import already in progress for {exp_dir.name}")
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    events_imported=0,
                    conversations_imported=0,
                    error="Import in progress"
                )
            
            # Mark as importing
            importing_marker.touch()
            
            try:
                # Load manifest
                with open(manifest_path) as f:
                    manifest_data = json.load(f)
                
                experiment_id = manifest_data.get("experiment_id", exp_dir.name)
                
                # Begin transaction for the import
                self.db.begin()
                
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
                
                # Commit transaction
                self.db.commit()
                
                # Create imported marker
                importing_marker.unlink()
                with open(imported_marker, 'w') as f:
                    json.dump({
                        "imported_at": datetime.now().isoformat(),
                        "events_count": events_count,
                        "conversations_count": conversations_count
                    }, f)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"Successfully imported {experiment_id}: "
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
            logger.error(f"Failed to import {exp_dir.name}: {e}")
            
            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                error=str(e),
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
        
        # Insert raw events with their JSON data
        for line_num, event in state.events:
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
            
            self.db.execute("""
                INSERT INTO events (
                    timestamp, event_type, conversation_id, 
                    experiment_id, event_data, sequence
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                event.timestamp.isoformat(),
                event.__class__.__name__,
                conversation_id,
                experiment_id,
                json.dumps(event_data, default=str),
                line_num
            ])
        
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
        
        # Insert messages
        for msg in state.messages:
            self.db.execute("""
                INSERT INTO messages (
                    conversation_id, turn_number, agent_id, 
                    content, timestamp, token_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                msg["conversation_id"],
                msg["turn_number"],
                msg["agent_id"],
                msg["content"],
                msg["timestamp"].isoformat() if isinstance(msg["timestamp"], datetime) else msg["timestamp"],
                msg["token_count"]
            ])
        
        # Insert turn metrics
        for metric in state.turn_metrics:
            self.db.execute("""
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score
                ) VALUES (?, ?, ?, ?)
            """, [
                metric["conversation_id"],
                metric["turn_number"],
                metric["timestamp"].isoformat() if isinstance(metric["timestamp"], datetime) else metric["timestamp"],
                metric["convergence_score"]
            ])
        
        return len(state.events)