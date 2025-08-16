"""New import service for wide-table conversation turns."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import duckdb

from ..io.logger import get_logger
from .importers import ConversationImporter, EventProcessor, MetricsImporter
from .schema_manager import SchemaManager

logger = get_logger("import_service")


@dataclass
class ImportResult:
    """Result of an import operation."""

    success: bool
    experiment_id: str
    turns_imported: int
    conversations_imported: int
    error: Optional[str] = None
    duration_seconds: float = 0.0


class ImportService:
    """Service for importing JSONL experiment data into DuckDB conversation_turns table.

    This service orchestrates the import process, delegating specific tasks to:
    - ConversationImporter: Handles conversation and message data
    - MetricsImporter: Handles metrics and turn data
    - EventProcessor: Processes JSONL files and coordinates importers
    """

    def __init__(self, db_path: str):
        """Initialize with database path.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.db = duckdb.connect(db_path)

        # Create schema manager and ensure schema exists
        self._schema_manager = SchemaManager()
        self._schema_manager.ensure_schema(self.db, db_path)

        # Initialize importers
        self.conversation_importer = ConversationImporter(self.db)
        self.metrics_importer = MetricsImporter(self.db)
        self.event_processor = EventProcessor(
            self.conversation_importer, self.metrics_importer
        )

    def import_experiment_from_jsonl(self, exp_dir: Path) -> ImportResult:
        """Import experiment data from JSONL files into conversation_turns table.

        Args:
            exp_dir: Directory containing manifest.json and JSONL files

        Returns:
            ImportResult with success status and counts
        """
        start_time = datetime.now()

        try:
            # Load manifest
            manifest_path = exp_dir / "manifest.json"
            if not manifest_path.exists():
                return ImportResult(
                    success=False,
                    experiment_id=exp_dir.name,
                    turns_imported=0,
                    conversations_imported=0,
                    error="No manifest.json found",
                )

            with open(manifest_path) as f:
                manifest = json.load(f)

            experiment_id = manifest.get("experiment_id", exp_dir.name)

            # Find all JSONL files
            jsonl_files = list(exp_dir.glob("*.jsonl"))
            if not jsonl_files:
                return ImportResult(
                    success=False,
                    experiment_id=experiment_id,
                    turns_imported=0,
                    conversations_imported=0,
                    error="No JSONL files found",
                )

            # Process each JSONL file (typically one per conversation)
            total_turns = 0
            conversations_processed = 0

            self.db.begin()

            # First, ensure experiment exists in database
            self.conversation_importer.ensure_experiment_exists(experiment_id, manifest)

            for jsonl_file in jsonl_files:
                turns_count, convs_created = self.event_processor.process_jsonl_file(
                    jsonl_file, experiment_id, manifest
                )
                total_turns += turns_count
                conversations_processed += convs_created

            self.db.commit()

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Successfully imported {experiment_id}: "
                f"{total_turns} turns, {conversations_processed} conversations"
            )

            return ImportResult(
                success=True,
                experiment_id=experiment_id,
                turns_imported=total_turns,
                conversations_imported=conversations_processed,
                duration_seconds=duration,
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to import {exp_dir.name}: {e}")

            return ImportResult(
                success=False,
                experiment_id=exp_dir.name,
                turns_imported=0,
                conversations_imported=0,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def import_all_pending(self, experiments_dir: Path) -> List[ImportResult]:
        """Import all experiments that have JSONL files but haven't been imported.

        Args:
            experiments_dir: Root directory containing experiment subdirectories

        Returns:
            List of ImportResults for each experiment
        """
        results: List[ImportResult] = []

        if not experiments_dir.exists():
            logger.warning(f"Experiments directory {experiments_dir} does not exist")
            return results

        # Find all experiment directories
        for exp_dir in experiments_dir.iterdir():
            if not exp_dir.is_dir() or exp_dir.name.startswith("."):
                continue

            # Check if it has a manifest
            if not (exp_dir / "manifest.json").exists():
                continue

            # Check if already imported (look for data in conversation_turns)
            experiment_id = exp_dir.name
            existing_count = self.db.execute(
                "SELECT COUNT(*) FROM conversation_turns WHERE experiment_id = ?",
                [experiment_id],
            ).fetchone()[0]

            if existing_count > 0:
                logger.info(
                    f"Experiment {experiment_id} already imported ({existing_count} turns)"
                )
                continue

            # Import the experiment
            result = self.import_experiment_from_jsonl(exp_dir)
            results.append(result)

        return results

    def close(self):
        """Close the database connection."""
        if self.db:
            self.db.close()
