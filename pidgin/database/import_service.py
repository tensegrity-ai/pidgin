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
        events_imported = 0
        conversation_data = {}
        pending_messages = []  # Store messages until conversation is created
        pending_metrics = []   # Store metrics until conversation is created
        token_counts = {}      # Map (agent_id, turn_num) -> token_count
        
        # First pass: Read JSONL and collect data
        with open(jsonl_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line.strip())
                    
                    # Insert event into events table
                    self.db.execute("""
                        INSERT INTO events (
                            timestamp, event_type, conversation_id, 
                            experiment_id, event_data, sequence
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        event.get("timestamp"),
                        event.get("event_type"),
                        conversation_id,
                        experiment_id,
                        json.dumps(event),
                        line_num
                    ])
                    events_imported += 1
                    
                    # Process specific event types for structured data
                    event_type = event.get("event_type")
                    
                    if event_type == "ConversationStartEvent":
                        # Extract conversation metadata
                        conversation_data.update({
                            "agent_a_model": event.get("agent_a_model"),
                            "agent_b_model": event.get("agent_b_model"),
                            "max_turns": event.get("max_turns"),
                            "initial_prompt": event.get("initial_prompt"),
                            "started_at": event.get("timestamp")
                        })
                    
                    elif event_type == "MessageCompleteEvent":
                        # Store token count for this agent
                        agent_id = event.get("agent_id")
                        tokens_used = event.get("tokens_used", 0)
                        token_counts[agent_id] = tokens_used
                    
                    elif event_type == "TurnCompleteEvent":
                        turn_num = event.get("turn_number", 0)
                        turn = event.get("turn", {})
                        
                        # Extract messages from turn data
                        msg_a = turn.get("agent_a_message", {})
                        msg_b = turn.get("agent_b_message", {})
                        
                        # Store messages for this turn
                        if msg_a.get("content"):
                            pending_messages.append({
                                "conversation_id": conversation_id,
                                "turn_number": turn_num,
                                "agent_id": "agent_a",
                                "content": msg_a.get("content", ""),
                                "timestamp": msg_a.get("timestamp"),
                                "token_count": token_counts.get("agent_a", 0)
                            })
                        
                        if msg_b.get("content"):
                            pending_messages.append({
                                "conversation_id": conversation_id,
                                "turn_number": turn_num,
                                "agent_id": "agent_b", 
                                "content": msg_b.get("content", ""),
                                "timestamp": msg_b.get("timestamp"),
                                "token_count": token_counts.get("agent_b", 0)
                            })
                        
                        # Store turn metrics for later insertion
                        pending_metrics.append({
                            "conversation_id": conversation_id,
                            "turn_number": turn_num,
                            "timestamp": event.get("timestamp"),
                            "convergence_score": event.get("convergence_score", 0.0)
                        })
                        
                        # Update conversation data
                        conversation_data["final_convergence_score"] = event.get("convergence_score")
                        conversation_data["total_turns"] = turn_num
                    
                    elif event_type == "ConversationEndEvent":
                        conversation_data.update({
                            "status": "completed",
                            "completed_at": event.get("timestamp"),
                            "total_turns": event.get("total_turns", 0),
                            "convergence_reason": event.get("reason")
                        })
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line {line_num} in {jsonl_path}: {e}")
                    continue
        
        # Create conversation record first (to satisfy foreign key constraints)
        if conversation_data:
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
                    conversation_data.get("status", "unknown"),
                    conversation_data.get("completed_at"),
                    conversation_data.get("total_turns", 0),
                    conversation_data.get("final_convergence_score"),
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
                    conversation_data.get("started_at"),
                    conversation_data.get("completed_at"),
                    conversation_data.get("status", "unknown"),
                    conversation_data.get("agent_a_model"),
                    conversation_data.get("agent_b_model"),
                    conversation_data.get("max_turns"),
                    conversation_data.get("total_turns", 0),
                    conversation_data.get("initial_prompt"),
                    conversation_data.get("final_convergence_score")
                ])
        
        # Now insert messages
        for msg in pending_messages:
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
                msg["timestamp"],
                msg["token_count"]
            ])
        
        # Insert turn metrics
        for metric in pending_metrics:
            self.db.execute("""
                INSERT INTO turn_metrics (
                    conversation_id, turn_number, timestamp,
                    convergence_score
                ) VALUES (?, ?, ?, ?)
            """, [
                metric["conversation_id"],
                metric["turn_number"],
                metric["timestamp"],
                metric["convergence_score"]
            ])
        
        return events_imported