# pidgin/database/batch_importer.py
"""Batch importer for loading JSONL experiments into DuckDB."""

import json
import duckdb
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..experiments.manifest import ManifestManager
from ..io.logger import get_logger

logger = get_logger("batch_importer")


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    experiment_id: str
    events_imported: int
    conversations_imported: int
    error: Optional[str] = None
    duration_seconds: float = 0.0


class BatchImporter:
    """Imports JSONL experiment data into DuckDB for analysis."""
    
    def __init__(self, db_path: Path):
        """Initialize importer with database path.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure database schema exists."""
        from .schema import EVENT_SCHEMA, EXPERIMENTS_SCHEMA, CONVERSATIONS_SCHEMA, TURN_METRICS_SCHEMA
        
        with duckdb.connect(str(self.db_path)) as conn:
            # Create tables
            conn.execute(EVENT_SCHEMA)
            conn.execute(EXPERIMENTS_SCHEMA)
            conn.execute(CONVERSATIONS_SCHEMA)
            conn.execute(TURN_METRICS_SCHEMA)
            
            logger.info("Database schema ensured")
    
    def import_experiment(self, exp_dir: Path, force: bool = False) -> ImportResult:
        """Import a single experiment from JSONL files.
        
        Args:
            exp_dir: Experiment directory containing manifest and JSONL files
            force: Force reimport even if already imported
            
        Returns:
            ImportResult with status and statistics
        """
        start_time = datetime.now()
        
        # Check if already imported
        imported_marker = exp_dir / ".imported"
        if imported_marker.exists() and not force:
            logger.info(f"Experiment {exp_dir.name} already imported, skipping")
            return ImportResult(
                success=True,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                duration_seconds=0
            )
        
        # Create importing marker
        importing_marker = exp_dir / ".importing"
        importing_marker.touch()
        
        try:
            # Read manifest
            manifest = ManifestManager(exp_dir)
            manifest_data = manifest.get_manifest()
            
            if not manifest_data:
                raise ValueError(f"No manifest found in {exp_dir}")
            
            experiment_id = manifest_data["experiment_id"]
            
            # Import to database
            with duckdb.connect(str(self.db_path)) as conn:
                # Start transaction
                conn.begin()
                
                try:
                    # Import experiment record
                    self._import_experiment_record(conn, manifest_data)
                    
                    # Import conversations and events
                    events_count = 0
                    conversations_count = 0
                    
                    for conv_id, conv_info in manifest_data.get("conversations", {}).items():
                        jsonl_path = exp_dir / conv_info["jsonl"]
                        if jsonl_path.exists():
                            event_count = self._import_conversation(
                                conn, experiment_id, conv_id, jsonl_path
                            )
                            events_count += event_count
                            conversations_count += 1
                    
                    # Commit transaction
                    conn.commit()
                    
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
                    conn.rollback()
                    raise
                    
        except Exception as e:
            # Clean up importing marker
            if importing_marker.exists():
                importing_marker.unlink()
            
            logger.error(f"Failed to import {exp_dir.name}: {e}")
            
            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                events_imported=0,
                conversations_imported=0,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _import_experiment_record(self, conn: duckdb.DuckDBPyConnection, 
                                manifest: Dict[str, Any]) -> None:
        """Import experiment metadata.
        
        Args:
            conn: Database connection
            manifest: Manifest data
        """
        # Check if experiment already exists
        result = conn.execute(
            "SELECT COUNT(*) FROM experiments WHERE experiment_id = ?",
            [manifest["experiment_id"]]
        ).fetchone()
        
        if result[0] > 0:
            # Update existing record
            conn.execute("""
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
            conn.execute("""
                INSERT INTO experiments (
                    experiment_id, name, created_at, started_at, completed_at,
                    status, config, total_conversations, 
                    completed_conversations, failed_conversations, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                manifest["experiment_id"],
                manifest.get("name", manifest["experiment_id"]),
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
    
    def _import_conversation(self, conn: duckdb.DuckDBPyConnection,
                           experiment_id: str, conversation_id: str,
                           jsonl_path: Path) -> int:
        """Import a single conversation from JSONL.
        
        Args:
            conn: Database connection
            experiment_id: Parent experiment ID
            conversation_id: Conversation ID
            jsonl_path: Path to JSONL file
            
        Returns:
            Number of events imported
        """
        events_imported = 0
        conversation_data = {}
        metrics_data = {}
        
        # Read and process JSONL
        with open(jsonl_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line.strip())
                    
                    # Insert event
                    conn.execute("""
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
                    
                    # Extract conversation metadata from ConversationStartEvent
                    if event.get("event_type") == "ConversationStartEvent":
                        conversation_data.update({
                            "agent_a_model": event.get("agent_a_model"),
                            "agent_b_model": event.get("agent_b_model"),
                            "max_turns": event.get("max_turns"),
                            "initial_prompt": event.get("initial_prompt"),
                            "started_at": event.get("timestamp")
                        })
                    
                    # Extract end status from ConversationEndEvent
                    elif event.get("event_type") == "ConversationEndEvent":
                        conversation_data.update({
                            "status": "completed",
                            "completed_at": event.get("timestamp"),
                            "final_turn": event.get("final_turn", 0)
                        })
                    
                    # Collect metrics from TurnCompleteEvent
                    elif event.get("event_type") == "TurnCompleteEvent":
                        turn_num = event.get("turn_number", 0)
                        if convergence := event.get("convergence_score"):
                            metrics_data[f"turn_{turn_num}_convergence"] = convergence
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line {line_num} in {jsonl_path}: {e}")
                    continue
        
        # Insert conversation record
        if conversation_data:
            # Check if conversation already exists
            result = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE conversation_id = ?",
                [conversation_id]
            ).fetchone()
            
            if result[0] > 0:
                # Update existing
                conn.execute("""
                    UPDATE conversations SET
                        status = ?,
                        completed_at = ?,
                        total_turns = ?
                    WHERE conversation_id = ?
                """, [
                    conversation_data.get("status", "unknown"),
                    conversation_data.get("completed_at"),
                    conversation_data.get("final_turn", 0),
                    conversation_id
                ])
            else:
                # Insert new
                conn.execute("""
                    INSERT INTO conversations (
                        conversation_id, experiment_id, started_at, completed_at,
                        status, agent_a_model, agent_b_model, max_turns, 
                        total_turns, initial_prompt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    conversation_id,
                    experiment_id,
                    conversation_data.get("started_at"),
                    conversation_data.get("completed_at"),
                    conversation_data.get("status", "unknown"),
                    conversation_data.get("agent_a_model"),
                    conversation_data.get("agent_b_model"),
                    conversation_data.get("max_turns"),
                    conversation_data.get("final_turn", 0),
                    conversation_data.get("initial_prompt")
                ])
        
        return events_imported
    
    def import_all_unimported(self, experiments_dir: Path) -> List[ImportResult]:
        """Import all experiments that haven't been imported yet.
        
        Args:
            experiments_dir: Base experiments directory
            
        Returns:
            List of import results
        """
        results = []
        
        for exp_dir in experiments_dir.glob("exp_*"):
            if not exp_dir.is_dir():
                continue
            
            # Skip if already imported
            if (exp_dir / ".imported").exists():
                continue
            
            logger.info(f"Importing {exp_dir.name}")
            result = self.import_experiment(exp_dir)
            results.append(result)
        
        return results