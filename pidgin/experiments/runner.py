# pidgin/experiments/runner.py
"""Experiment runner supporting both sequential and parallel execution."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from ..core.app_context import AppContext
from ..core.constants import ExperimentStatus
from ..core.event_bus import EventBus
from ..core.events import ExperimentCompleteEvent
from ..ui.display_utils import DisplayUtils
from .config import ExperimentConfig
from .conversation_orchestrator import ConversationOrchestrator
from .daemon import ExperimentDaemon
from .experiment_setup import ExperimentSetup
from .manifest import ManifestManager
from .post_processor import PostProcessor


class ExperimentRunner:
    """Runs experiment conversations with configurable parallelism."""

    def __init__(
        self,
        output_dir: Path,
        app_context: Optional[AppContext] = None,
        daemon: Optional[ExperimentDaemon] = None,
    ):
        """Initialize experiment runner.

        Args:
            output_dir: Base output directory for experiments
            app_context: Optional application context with dependencies
            daemon: Optional daemon instance for stop detection
        """
        self.output_dir = output_dir
        self.console = Console()
        self.display = DisplayUtils(self.console)
        self.daemon = daemon
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_count = 0
        self.failed_count = 0
        self.experiment_event_bus: Optional[EventBus] = None

        # Create app context if not provided
        self.app_context = app_context or AppContext()

        # Initialize helper classes
        self.setup = ExperimentSetup()
        self.orchestrator = ConversationOrchestrator(self.app_context, daemon)

    async def run_experiment_with_id(
        self, experiment_id: str, experiment_dir: str, config: ExperimentConfig
    ):
        """Run experiment with existing ID.

        Args:
            experiment_id: Existing experiment ID
            experiment_dir: Directory name to use for the experiment
            config: Experiment configuration
        """
        exp_dir = self.output_dir / experiment_dir
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = self.setup.create_manifest(exp_dir, experiment_id, config)

        # Create experiment-level event bus
        self.experiment_event_bus = EventBus(event_log_dir=exp_dir)
        await self.experiment_event_bus.start()

        # Create PostProcessor to handle post-processing
        post_processor = PostProcessor(self.experiment_event_bus, self.output_dir)

        try:
            # Validate API keys
            self.setup.validate_api_keys(config)

            # Run conversations based on parallel configuration
            if config.max_parallel > 1:
                await self._run_parallel_conversations(experiment_id, config, exp_dir)
            else:
                # Sequential execution
                for i in range(config.repetitions):
                    if self.daemon and self.daemon.stop_requested:
                        logging.info("Stop requested, breaking conversation loop")
                        break

                    conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
                    await self._run_single_conversation(
                        experiment_id, conversation_id, config, {}, exp_dir
                    )

                    # Update counts
                    self.completed_count += 1
                    manifest.update_conversation_status(
                        conversation_id,
                        "completed",
                        self.completed_count,
                        self.failed_count,
                    )

            # Emit experiment complete event
            await self.experiment_event_bus.emit(
                ExperimentCompleteEvent(
                    experiment_id=experiment_id,
                    completed_conversations=self.completed_count,
                    failed_conversations=self.failed_count,
                    total_conversations=config.repetitions,
                    status=ExperimentStatus.COMPLETED,
                )
            )

            # Wait for post-processing to complete
            await post_processor.wait_for_completion()

        except Exception as e:
            logging.error(f"Experiment failed: {e}", exc_info=True)

            # Update manifest status
            manifest.update_experiment_status(
                status=ExperimentStatus.FAILED, error=str(e)
            )

            await self.experiment_event_bus.emit(
                ExperimentCompleteEvent(
                    experiment_id=experiment_id,
                    completed_conversations=self.completed_count,
                    failed_conversations=self.failed_count,
                    total_conversations=config.repetitions,
                    status=ExperimentStatus.FAILED,
                )
            )
            raise
        finally:
            # Stop the experiment event bus
            await self.experiment_event_bus.stop()

            # Final manifest update
            manifest.update_experiment_status(status=ExperimentStatus.COMPLETED)

    async def _run_parallel_conversations(
        self, experiment_id: str, config: ExperimentConfig, exp_dir: Path
    ):
        """Run conversations in parallel with rate limiting.

        Args:
            experiment_id: Parent experiment ID
            config: Experiment configuration
            exp_dir: Experiment directory
        """
        semaphore = asyncio.Semaphore(config.max_parallel)
        tasks = []

        async def run_with_semaphore(conv_id: str, conv_config: dict):
            async with semaphore:
                try:
                    await self._run_single_conversation(
                        experiment_id, conv_id, config, conv_config, exp_dir
                    )
                    self.completed_count += 1
                except Exception as e:
                    logging.error(f"Conversation {conv_id} failed: {e}")
                    self.failed_count += 1
                finally:
                    # Update manifest
                    manifest = ManifestManager(exp_dir)
                    manifest.update_conversation_status(
                        conv_id,
                        "completed" if conv_id not in self.active_tasks else "failed",
                        self.completed_count,
                        self.failed_count,
                    )

        # Create all conversation tasks
        for i in range(config.repetitions):
            if self.daemon and self.daemon.stop_requested:
                logging.info("Stop requested during parallel task creation")
                break

            conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
            task = asyncio.create_task(run_with_semaphore(conversation_id, {}))
            tasks.append(task)
            self.active_tasks[conversation_id] = task

        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clear active tasks
        self.active_tasks.clear()

        logging.info(f"Completed: {self.completed_count}, Failed: {self.failed_count}")

    async def _run_single_conversation(
        self,
        experiment_id: str,
        conversation_id: str,
        config: ExperimentConfig,
        conv_config: Dict[str, Any],
        exp_dir: Path,
    ):
        """Run a single conversation with metrics capture.

        Args:
            experiment_id: Parent experiment ID
            conversation_id: Unique conversation ID
            config: Experiment configuration
            conv_config: Conversation-specific configuration
            exp_dir: Experiment directory
        """
        try:
            import setproctitle

            setproctitle.setproctitle("pidgin-exp")
        except ImportError:
            pass

        self.orchestrator.register_conversation(exp_dir, conversation_id)
        event_bus = await self.setup.setup_event_bus(exp_dir, conversation_id)

        try:
            agents, providers = await self.setup.create_agents_and_providers(config)

            output_manager, console = self.setup.setup_output_and_console(
                config, exp_dir, conversation_id
            )

            await self.orchestrator.handle_branching(
                config=config,
                agents=agents,
                providers=providers,
                output_manager=output_manager,
                console=console,
                event_bus=event_bus,
                conversation_id=conversation_id,
                branch_from=config.branch_from_conversation,
                branch_at=config.branch_from_turn,
                experiment_id=experiment_id,
            )

        finally:
            await event_bus.stop()
