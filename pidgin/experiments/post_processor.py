# pidgin/experiments/post_processor.py
"""Post-experiment processing service with FIFO queue."""

import asyncio
import json
import logging
from asyncio import Queue
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.event_bus import EventBus
from ..core.events import (
    ExperimentCompleteEvent,
    PostProcessingCompleteEvent,
    PostProcessingStartEvent,
)
from ..database.event_store import EventStore
from ..database.transcript_generator import TranscriptGenerator
from ..io.paths import get_database_path
from .manifest import ManifestManager

logger = logging.getLogger(__name__)


class PostProcessor:
    """Handles post-experiment processing with sequential FIFO queue."""

    def __init__(self, event_bus: EventBus, experiments_dir: Path):
        """Initialize post processor.

        Args:
            event_bus: Global event bus to subscribe to
            experiments_dir: Root directory containing experiments
        """
        self.bus = event_bus
        self.experiments_dir = experiments_dir
        self.queue: Queue[Any] = asyncio.Queue()
        self.processing = False

        # Subscribe to experiment completion events
        self.bus.subscribe(
            ExperimentCompleteEvent, self._sync_handle_experiment_complete
        )

    def _sync_handle_experiment_complete(self, event: ExperimentCompleteEvent) -> None:
        """Sync wrapper for async handler."""
        asyncio.create_task(self.handle_experiment_complete(event))

    async def wait_for_completion(self):
        """Wait for all queued post-processing to complete.

        This method blocks until the queue is empty and processing is done.
        """
        # Wait for queue to be empty
        await self.queue.join()

        # Wait a bit more to ensure the last item finishes processing
        await asyncio.sleep(0.5)

    async def handle_experiment_complete(self, event: ExperimentCompleteEvent):
        """Queue experiment for post-processing.

        Args:
            event: ExperimentCompleteEvent with experiment details
        """
        # Only process successfully completed experiments
        if event.status != "completed":
            logger.info(
                f"Skipping post-processing for {event.experiment_id} "
                f"(status: {event.status})"
            )
            return

        # Find experiment directory
        exp_dir = None
        for child in self.experiments_dir.iterdir():
            if child.is_dir():
                manifest_path = child / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        if manifest.get("experiment_id") == event.experiment_id:
                            exp_dir = child
                            break

        if not exp_dir:
            logger.error(
                f"Could not find directory for experiment {event.experiment_id}"
            )
            return

        # Queue for processing
        await self.queue.put(
            {"experiment_id": event.experiment_id, "experiment_dir": exp_dir}
        )

        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self.process_queue())

    async def process_queue(self):
        """Process queued experiments sequentially."""
        self.processing = True

        try:
            while not self.queue.empty():
                item = await self.queue.get()
                try:
                    await self.process_experiment(
                        item["experiment_id"], item["experiment_dir"]
                    )
                finally:
                    # Mark task as done for wait_for_completion
                    self.queue.task_done()
        finally:
            self.processing = False

    async def process_experiment(self, experiment_id: str, exp_dir: Path):
        """Process a single experiment.

        Args:
            experiment_id: Experiment ID
            exp_dir: Experiment directory path
        """
        logger.info(f"Starting post-processing for experiment {experiment_id}")

        # Create post-processing log
        log_path = exp_dir / "post_processing.log"
        with open(log_path, "w") as log_file:
            start_time = datetime.now()
            log_file.write("Post-Processing Log\n")
            log_file.write("==================\n")
            log_file.write(f"Experiment ID: {experiment_id}\n")
            log_file.write(f"Started: {start_time.isoformat()}\n\n")

            # Track what we're doing
            tasks = ["README", "Jupyter notebook", "Database import", "Transcripts"]

            # Emit start event
            start_event = PostProcessingStartEvent(
                experiment_id=experiment_id,
                tasks=tasks,
            )
            await self.bus.emit(start_event)

            steps_completed = []
            steps_failed = []

            # Update manifest status
            manifest = ManifestManager(exp_dir)
            manifest.update_experiment_status("post_processing")

            # 1. Import to database and run post-processing with same EventStore
            log_file.write(f"[{datetime.now().isoformat()}] Importing to database...\n")
            try:
                db_path = get_database_path()
                with EventStore(db_path) as event_store:
                    # Import experiment data
                    result = event_store.import_experiment_from_jsonl(exp_dir)

                    if result.success:
                        steps_completed.append("Database import")
                        log_file.write(
                            f"[{datetime.now().isoformat()}] ✓ Database import complete\n"
                        )

                        # 2. Generate Jupyter notebook (using same EventStore)
                        log_file.write(
                            f"[{datetime.now().isoformat()}] Generating notebook...\n"
                        )
                        try:
                            from ..analysis.notebook_generator import NotebookGenerator

                            notebook_gen = NotebookGenerator(exp_dir, event_store)
                            if notebook_gen.generate():
                                steps_completed.append("Jupyter notebook")
                                log_file.write(
                                    f"[{datetime.now().isoformat()}] ✓ Notebook generated\n"
                                )
                            else:
                                log_file.write(
                                    f"[{datetime.now().isoformat()}] - Notebook skipped (nbformat not installed)\n"
                                )
                        except ImportError:
                            log_file.write(
                                f"[{datetime.now().isoformat()}] - Notebook skipped (import error)\n"
                            )
                        except Exception as e:
                            logger.error(f"Failed to generate notebook: {e}")
                            steps_failed.append("Jupyter notebook")
                            log_file.write(
                                f"[{datetime.now().isoformat()}] ✗ Notebook failed: {e}\n"
                            )

                        # 3. Generate transcripts (using same EventStore)
                        log_file.write(
                            f"[{datetime.now().isoformat()}] Generating transcripts...\n"
                        )
                        try:
                            generator = TranscriptGenerator(event_store)
                            generator.generate_experiment_transcripts(
                                experiment_id, exp_dir
                            )
                            steps_completed.append("Transcripts")
                            log_file.write(
                                f"[{datetime.now().isoformat()}] ✓ Transcripts generated\n"
                            )
                        except Exception as e:
                            logger.error(f"Failed to generate transcripts: {e}")
                            steps_failed.append("Transcripts")
                            log_file.write(
                                f"[{datetime.now().isoformat()}] ✗ Transcripts failed: {e}\n"
                            )
                    else:
                        steps_failed.append("Database import")
                        log_file.write(
                            f"[{datetime.now().isoformat()}] ✗ Database import failed: {result.error}\n"
                        )
            except Exception as e:
                logger.error(f"Failed to import to database: {e}")
                steps_failed.append("Database import")
                log_file.write(
                    f"[{datetime.now().isoformat()}] ✗ Database import failed: {e}\n"
                )

            # Complete
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            log_file.write(f"\nCompleted: {end_time.isoformat()}\n")
            log_file.write(f"Duration: {duration:.1f} seconds\n")
            log_file.write(
                f"Tasks completed: {', '.join(steps_completed) if steps_completed else 'None'}\n"
            )
            log_file.write(
                f"Tasks failed: {', '.join(steps_failed) if steps_failed else 'None'}\n"
            )

            # Emit complete event
            duration_ms = int(duration * 1000)
            complete_event = PostProcessingCompleteEvent(
                experiment_id=experiment_id,
                tasks_completed=steps_completed,
                tasks_failed=steps_failed,
                duration_ms=duration_ms,
            )
            await self.bus.emit(complete_event)

            # Update manifest back to completed
            manifest.update_experiment_status("completed")

            logger.info(
                f"Post-processing complete for {experiment_id}: "
                f"{len(steps_completed)} succeeded, {len(steps_failed)} failed"
            )
