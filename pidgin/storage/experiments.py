"""Experiment storage and persistence."""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import pickle

from pidgin.core.experiment import Experiment, ExperimentConfig, ExperimentStatus
from pidgin.llm.factory import create_llm


class ExperimentStorage:
    """Storage manager for experiments."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite database for metadata
        self.db_path = self.data_dir / "experiments.db"
        self._init_db()
        
        # Directory for full experiment data
        self.experiments_dir = self.data_dir / "experiments"
        self.experiments_dir.mkdir(exist_ok=True)
    
    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    config TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON experiments(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON experiments(created_at)
            """)
    
    def save(self, experiment: Experiment):
        """Save an experiment."""
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO experiments 
                (id, name, status, created_at, updated_at, config, metrics, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.id,
                experiment.config.name,
                experiment.status,
                experiment.created_at.isoformat(),
                datetime.utcnow().isoformat(),
                json.dumps(self._config_to_dict(experiment.config)),
                json.dumps(self._metrics_to_dict(experiment.metrics)),
                json.dumps(experiment.metadata)
            ))
        
        # Save full experiment data
        experiment_path = self.experiments_dir / f"{experiment.id}.pkl"
        with open(experiment_path, "wb") as f:
            pickle.dump(experiment, f)
    
    def load(self, experiment_id: str) -> Optional[Experiment]:
        """Load an experiment by ID."""
        experiment_path = self.experiments_dir / f"{experiment_id}.pkl"
        
        if experiment_path.exists():
            try:
                with open(experiment_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                # Fallback to reconstructing from database
                pass
        
        # Try to reconstruct from database
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM experiments WHERE id = ?",
                (experiment_id,)
            ).fetchone()
            
            if row:
                return self._reconstruct_experiment(dict(row))
        
        return None
    
    def list(
        self,
        status: Optional[ExperimentStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filtering."""
        query = "SELECT * FROM experiments"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            
            return [dict(row) for row in rows]
    
    def delete(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        # Delete from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
        
        # Delete data file
        experiment_path = self.experiments_dir / f"{experiment_id}.pkl"
        if experiment_path.exists():
            experiment_path.unlink()
            return True
        
        return False
    
    def get_transcript_path(self, experiment_id: str) -> Path:
        """Get the path for an experiment's transcript."""
        transcript_dir = self.data_dir / "transcripts"
        transcript_dir.mkdir(exist_ok=True)
        return transcript_dir / f"{experiment_id}.json"
    
    def save_transcript(self, experiment: Experiment):
        """Save experiment transcript."""
        transcript_path = self.get_transcript_path(experiment.id)
        
        transcript = {
            "experiment": experiment.to_dict(),
            "conversation": experiment.conversation_history,
            "exported_at": datetime.utcnow().isoformat()
        }
        
        with open(transcript_path, "w") as f:
            json.dump(transcript, f, indent=2)
    
    def _config_to_dict(self, config: ExperimentConfig) -> Dict[str, Any]:
        """Convert config to dictionary for storage."""
        return {
            "name": config.name,
            "max_turns": config.max_turns,
            "mediation_level": config.mediation_level.value,
            "compression_enabled": config.compression_enabled,
            "compression_start_turn": config.compression_start_turn,
            "compression_rate": config.compression_rate,
            "meditation_mode": config.meditation_mode,
            "meditation_style": config.meditation_style,
            "basin_detection": config.basin_detection,
        }
    
    def _metrics_to_dict(self, metrics) -> Dict[str, Any]:
        """Convert metrics to dictionary for storage."""
        return {
            "total_turns": metrics.total_turns,
            "total_tokens": metrics.total_tokens,
            "compression_ratio": metrics.compression_ratio,
            "symbols_emerged": metrics.symbols_emerged,
            "basin_reached": metrics.basin_reached,
            "start_time": metrics.start_time.isoformat() if metrics.start_time else None,
            "end_time": metrics.end_time.isoformat() if metrics.end_time else None,
        }
    
    def _reconstruct_experiment(self, row: Dict[str, Any]) -> Experiment:
        """Reconstruct experiment from database row."""
        # This is a simplified reconstruction
        # In production, you'd need to properly recreate LLMs with API keys
        config_data = json.loads(row["config"])
        config = ExperimentConfig(**config_data)
        
        # Create placeholder LLMs (would need proper reconstruction in production)
        llms = []
        
        experiment = Experiment(
            config=config,
            llms=llms,
            id=row["id"]
        )
        
        experiment.status = ExperimentStatus(row["status"])
        experiment.created_at = datetime.fromisoformat(row["created_at"])
        experiment.metadata = json.loads(row["metadata"])
        
        return experiment