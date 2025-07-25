# pidgin/experiments/runner.py
"""Experiment runner supporting both sequential and parallel execution."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console

from ..config.models import get_model_config
from ..config.prompts import build_initial_prompt
from ..constants import ExperimentStatus
from ..core.conductor import Conductor
from ..core.events import (
    ConversationBranchedEvent,
    ExperimentCompleteEvent,
    PostProcessingStartEvent,
    PostProcessingCompleteEvent,
)
from ..core.types import Agent
from ..database.event_store import EventStore
from ..database.transcript_generator import TranscriptGenerator
from ..io.paths import get_database_path
from ..providers.api_key_manager import APIKeyManager

# Import provider builder and prompt builder to avoid circular imports
from ..providers.builder import build_provider as get_provider_for_model
from ..ui.display_utils import DisplayUtils
from .config import ExperimentConfig
from .daemon import ExperimentDaemon
from .manifest import ManifestManager
from .tracking_event_bus import TrackingEventBus

# The functions are now imported above


class ExperimentRunner:
    """Runs experiment conversations with configurable parallelism."""

    def __init__(self, output_dir: Path, daemon: Optional[ExperimentDaemon] = None):
        """Initialize experiment runner.

        Args:
            output_dir: Base output directory for experiments
            daemon: Optional daemon instance for stop detection
        """
        self.output_dir = output_dir
        self.console = Console()
        self.display = DisplayUtils(self.console)
        self.daemon = daemon
        self.active_tasks = {}
        self.completed_count = 0
        self.failed_count = 0
        self.experiment_event_bus = None  # Will be created per experiment

    async def run_experiment_with_id(
        self, experiment_id: str, experiment_dir: str, config: ExperimentConfig
    ):
        """Run experiment with existing ID.

        This is called by the daemon after it has already created the experiment record.

        Args:
            experiment_id: Existing experiment ID
            experiment_dir: Directory name to use for the experiment
            config: Experiment configuration
        """
        exp_dir = self.output_dir / experiment_dir
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = ManifestManager(exp_dir)
        manifest.create(
            experiment_id=experiment_id,
            name=config.name,
            config=config.dict(),
            total_conversations=config.repetitions,
        )

        # Removed legacy metadata.json - using only manifest.json

        # Create experiment-level event bus for tracking experiment-wide events
        from ..core.event_bus import EventBus
        self.experiment_event_bus = EventBus(event_log_dir=exp_dir)
        await self.experiment_event_bus.start()

        try:
            # Validate API keys for all required providers
            providers = set()
            agent_a_config = get_model_config(config.agent_a_model)
            agent_b_config = get_model_config(config.agent_b_model)
            if agent_a_config:
                providers.add(agent_a_config.provider)
            if agent_b_config:
                providers.add(agent_b_config.provider)

            # Check all providers have API keys before starting
            APIKeyManager.validate_required_providers(list(providers))

            # Prepare conversation configs
            conversations = []
            for i in range(config.repetitions):
                conv_id = f"conv_{experiment_id}_{uuid.uuid4().hex[:8]}"

                # Create conversation config
                conv_config = {
                    "conversation_id": conv_id,
                    "agent_a_model": config.agent_a_model,
                    "agent_b_model": config.agent_b_model,
                    "initial_prompt": config.custom_prompt,
                    "max_turns": config.max_turns,
                    "temperature_a": config.temperature_a,
                    "temperature_b": config.temperature_b,
                    "first_speaker": config.first_speaker,
                }

                conversations.append((conv_id, conv_config))

            # Run conversations with controlled parallelism
            await self._run_parallel_conversations(
                experiment_id, config, conversations, exp_dir
            )

            # Update final status
            if self.daemon and self.daemon.is_stopping():
                final_status = ExperimentStatus.INTERRUPTED
            else:
                final_status = ExperimentStatus.COMPLETED

            # Emit experiment complete event
            complete_event = ExperimentCompleteEvent(
                experiment_id=experiment_id,
                total_conversations=config.repetitions,
                completed_conversations=self.completed_count,
                failed_conversations=self.failed_count,
                status=final_status,
            )
            await self.experiment_event_bus.emit(complete_event)

            # Update manifest to post-processing status if completed
            if final_status == ExperimentStatus.COMPLETED:
                manifest.update_experiment_status(ExperimentStatus.POST_PROCESSING)
            else:
                manifest.update_experiment_status(final_status)

            # Metadata tracking removed - using only manifest.json

            logging.info(
                f"Experiment {experiment_id} completed with status: {final_status}"
            )

            # Automatically import to database and generate transcripts
            if final_status == ExperimentStatus.COMPLETED:
                await self._import_and_generate_transcripts(experiment_id, exp_dir, manifest)

        except Exception as e:
            logging.error(f"Experiment failed: {e}", exc_info=True)

            # Update manifest with error status
            manifest.update_experiment_status(ExperimentStatus.FAILED, error=str(e))

            # Metadata tracking removed - using only manifest.json

            raise
        finally:
            # Clean up experiment event bus
            if self.experiment_event_bus:
                await self.experiment_event_bus.stop()

    async def _run_parallel_conversations(
        self,
        experiment_id: str,
        config: ExperimentConfig,
        conversations: List[Tuple[str, Dict]],
        exp_dir: Path,
    ):
        """Run conversations in parallel with rate limit awareness.

        Args:
            experiment_id: Experiment ID
            config: Experiment configuration
            conversations: List of (conversation_id, config) tuples
        """
        # Determine parallelism based on rate limits
        # Start conservative, can be tuned based on provider limits
        max_parallel = min(config.max_parallel, 5)  # Cap at 5 for safety

        logging.info(
            f"Running {len(conversations)} conversations with "
            f"parallelism={max_parallel}"
        )

        # Use semaphore to control parallelism
        semaphore = asyncio.Semaphore(max_parallel)

        total = len(conversations)

        async def run_with_semaphore(conv_id: str, conv_config: Dict):
            """Run single conversation with semaphore control."""
            async with semaphore:
                # Check if daemon wants to stop
                if self.daemon and self.daemon.is_stopping():
                    logging.info(f"Skipping {conv_id} due to stop request")
                    return

                try:
                    logging.info(f"Starting {conv_id}")
                    await self._run_single_conversation(
                        experiment_id, conv_id, config, conv_config, exp_dir
                    )
                    self.completed_count += 1
                    logging.info(
                        f"Completed {conv_id} ({self.completed_count}/{total})"
                    )

                except asyncio.CancelledError:
                    # Handle graceful cancellation
                    logging.info(f"Cancelled {conv_id}")
                    raise
                except Exception as e:
                    self.failed_count += 1
                    logging.error(f"Failed {conv_id}: {e}", exc_info=True)

                    # Write error to conversation metadata
                    # Error already tracked in manifest.json

        # Create all tasks with staggered start times
        tasks = []
        for i, (conv_id, conv_config) in enumerate(conversations):
            if self.daemon and self.daemon.is_stopping():
                break
            task = asyncio.create_task(run_with_semaphore(conv_id, conv_config))
            tasks.append(task)
            self.active_tasks[id(task)] = task

            # Add delay between task creation to avoid thundering herd
            # This helps prevent initial bursts of API calls
            if i < len(conversations) - 1:
                await asyncio.sleep(
                    2.0
                )  # 2 second delay between starting conversations

        # Wait for all to complete or cancellation
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any exceptions that weren't already handled
            for i, result in enumerate(results):
                if isinstance(result, Exception) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    logging.error(f"Task {i} exception: {result}")

        except asyncio.CancelledError:
            # Daemon is stopping, cancel all tasks
            logging.info("Cancelling all active conversations...")
            for task in self.active_tasks.values():
                if not task.done():
                    task.cancel()

            # Wait for cancellations to complete
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
            raise
        finally:
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
        """
        # Set process title for this conversation
        try:
            import setproctitle

            setproctitle.setproctitle("pidgin-exp")
        except ImportError:
            pass  # Optional dependency

        # Register conversation in manifest
        self._register_conversation(exp_dir, conversation_id)

        # Set up event bus
        event_bus = await self._setup_event_bus(exp_dir, conversation_id)

        try:
            # Create agents and providers
            agents, providers = await self._create_agents_and_providers(config)

            # Set up output and console
            output_manager, console = self._setup_output_and_console(
                config, exp_dir, conversation_id
            )

            # Emit branch event if this is a branched conversation
            if config.branch_from_conversation:
                branch_event = ConversationBranchedEvent(
                    conversation_id=conversation_id,
                    source_conversation_id=config.branch_from_conversation,
                    branch_point=config.branch_from_turn or 0,
                    parameter_changes={
                        "agent_a_model": config.agent_a_model,
                        "agent_b_model": config.agent_b_model,
                        "temperature_a": config.temperature_a,
                        "temperature_b": config.temperature_b,
                    },
                    experiment_id=experiment_id,
                )
                await event_bus.emit(branch_event)

            # Create and run conductor
            await self._create_and_run_conductor(
                config=config,
                agents=agents,
                providers=providers,
                output_manager=output_manager,
                console=console,
                event_bus=event_bus,
                conversation_id=conversation_id,
            )

        finally:
            # Stop the event bus
            await event_bus.stop()

    def _register_conversation(self, exp_dir: Path, conversation_id: str) -> None:
        """Register conversation in manifest."""
        manifest = ManifestManager(exp_dir)
        jsonl_filename = f"{conversation_id}_events.jsonl"
        manifest.add_conversation(conversation_id, jsonl_filename)

    async def _setup_event_bus(
        self, exp_dir: Path, conversation_id: str
    ) -> TrackingEventBus:
        """Create and start tracking event bus for conversation."""
        event_bus = TrackingEventBus(
            experiment_dir=exp_dir, conversation_id=conversation_id
        )
        await event_bus.start()
        return event_bus

    async def _create_agents_and_providers(
        self, config: ExperimentConfig
    ) -> tuple[dict, dict]:
        """Create agents and providers from configuration."""
        # Get model configs
        model_a_config = get_model_config(config.agent_a_model)
        model_b_config = get_model_config(config.agent_b_model)

        if not model_a_config or not model_b_config:
            raise ValueError("Invalid model configuration")

        # Create providers
        logging.info(f"Creating provider for agent_a: {config.agent_a_model}")
        try:
            provider_a = await get_provider_for_model(
                config.agent_a_model, temperature=config.temperature_a
            )
        except Exception as e:
            logging.error(f"Failed to create provider_a: {e}", exc_info=True)
            raise
            
        logging.info(f"Creating provider for agent_b: {config.agent_b_model}")
        try:
            provider_b = await get_provider_for_model(
                config.agent_b_model, temperature=config.temperature_b
            )
        except Exception as e:
            logging.error(f"Failed to create provider_b: {e}", exc_info=True)
            raise

        if not provider_a or not provider_b:
            raise ValueError("Failed to create providers")
        
        # Set allow_truncation on providers based on config
        provider_a.allow_truncation = config.allow_truncation
        provider_b.allow_truncation = config.allow_truncation
        
        logging.info(f"Providers created successfully")

        # Create agents with display names from model config
        agent_a = Agent(
            id="agent_a",
            model=model_a_config.model_id,
            model_display_name=model_a_config.display_name,
            temperature=config.temperature_a,
            display_name=model_a_config.display_name,  # Use the model's display name
        )

        agent_b = Agent(
            id="agent_b",
            model=model_b_config.model_id,
            model_display_name=model_b_config.display_name,
            temperature=config.temperature_b,
            display_name=model_b_config.display_name,  # Use the model's display name
        )

        agents = {"agent_a": agent_a, "agent_b": agent_b}
        providers = {"agent_a": provider_a, "agent_b": provider_b}
        
        logging.info(f"Agents created successfully")

        return agents, providers

    def _setup_output_and_console(
        self, config: ExperimentConfig, exp_dir: Path, conversation_id: str
    ) -> tuple:
        """Set up output manager and console for display."""
        # Create minimal output manager that returns the experiment directory
        from ..io.output_manager import OutputManager

        output_manager = OutputManager()
        # Override the create_conversation_dir to return the experiment directory
        output_manager.create_conversation_dir = lambda conv_id: (
            conversation_id,
            exp_dir,
        )

        # Check if we need a console for display modes
        console = None
        if config.display_mode in ["chat", "tail"]:
            console = Console()

        return output_manager, console

    async def _create_and_run_conductor(
        self,
        config: ExperimentConfig,
        agents: dict,
        providers: dict,
        output_manager,
        console,
        event_bus: TrackingEventBus,
        conversation_id: str,
    ) -> None:
        """Create conductor and run the conversation."""
        # Build initial prompt
        initial_prompt = build_initial_prompt(
            custom_prompt=config.custom_prompt,
            dimensions=config.dimensions,
        )

        # Create conductor with the isolated event bus
        conductor = Conductor(
            base_providers=providers,
            output_manager=output_manager,
            console=console,
            convergence_threshold_override=config.convergence_threshold,
            convergence_action_override=config.convergence_action,
            bus=event_bus,
        )

        # Run the conversation
        await conductor.run_conversation(
            agent_a=agents["agent_a"],
            agent_b=agents["agent_b"],
            initial_prompt=initial_prompt,
            max_turns=config.max_turns,
            display_mode=config.display_mode,
            show_timing=False,
            choose_names=config.choose_names,
            awareness_a=config.awareness_a or config.awareness,
            awareness_b=config.awareness_b or config.awareness,
            temperature_a=config.temperature_a or config.temperature,
            temperature_b=config.temperature_b or config.temperature,
            conversation_id=conversation_id,
            prompt_tag=config.prompt_tag,
            branch_messages=config.branch_messages,
        )

    async def _import_and_generate_transcripts(self, experiment_id: str, exp_dir: Path, manifest: ManifestManager):
        """Automatically import experiment to database and generate transcripts.

        Args:
            experiment_id: Experiment ID
            exp_dir: Experiment directory
            manifest: Manifest manager to update status
        """
        import time
        start_time = time.time()
        
        # Emit post-processing start event
        tasks = ["README", "Jupyter notebook", "Database import", "Transcripts"]
        start_event = PostProcessingStartEvent(
            experiment_id=experiment_id,
            tasks=tasks,
        )
        await self.experiment_event_bus.emit(start_event)
        
        try:
            # Track what we're doing for a clean summary at the end
            steps_completed = []
            steps_failed = []

            # Generate README first
            logging.debug(f"Generating README for experiment {experiment_id}")
            try:
                from .readme_generator import ExperimentReadmeGenerator

                readme_gen = ExperimentReadmeGenerator(exp_dir)
                readme_gen.generate()
                steps_completed.append("README")
            except Exception as e:
                logging.error(f"Failed to generate README: {e}")
                steps_failed.append("README")

            # Generate Jupyter notebook
            logging.debug(
                f"Generating analysis notebook for experiment {experiment_id}"
            )
            try:
                from ..analysis.notebook_generator import NotebookGenerator

                notebook_gen = NotebookGenerator(exp_dir)
                notebook_gen.generate()
                steps_completed.append("Jupyter notebook")
            except ImportError:
                logging.debug(
                    "Jupyter notebook generation skipped (nbformat not installed)"
                )
            except Exception as e:
                logging.error(f"Failed to generate notebook: {e}")
                steps_failed.append("Jupyter notebook")

            logging.debug(f"Auto-importing experiment {experiment_id} to database")

            # Get database path
            db_path = get_database_path()

            # Import to database using EventStore
            try:
                with EventStore(db_path) as event_store:
                    result = event_store.import_experiment_from_jsonl(exp_dir)

                if result.success:
                    steps_completed.append("Database import")

                    # Generate transcripts
                    logging.debug(f"Generating transcripts for {experiment_id}")
                    try:
                        with TranscriptGenerator(db_path) as generator:
                            generator.generate_experiment_transcripts(experiment_id, exp_dir)
                        steps_completed.append("Transcripts")
                    except Exception as e:
                        logging.error(f"Failed to generate transcripts: {e}")
                        steps_failed.append("Transcripts")

                    # Show clean summary instead of multiple log lines
                    summary = f"✓ Post-processing complete: {', '.join(steps_completed)}"
                    if steps_failed:
                        summary += f"\n✗ Failed: {', '.join(steps_failed)}"

                    # Show summary in display mode appropriate way
                    if self.console:
                        self.display.info(summary, use_panel=False)
                else:
                    steps_failed.append("Database import")
            except Exception as e:
                logging.error(f"Failed to import to database: {e}")
                steps_failed.append("Database import")
                result = None
                
            if result and not result.success:
                # Display error in a nice panel
                error_message = "Database Import Failed\n\n"
                error_message += f"Experiment: {experiment_id}\n\n"
                error_message += f"Error: {result.error}"

                self.display.error(
                    error_message,
                    title="Import Error",
                    context="This usually means the database schema needs updating.",
                    use_panel=True,
                )

                # Don't double-log the error since we're showing it in a panel
                logging.debug(f"Import failed for {experiment_id}: {result.error}")

            # Emit post-processing complete event
            duration_ms = int((time.time() - start_time) * 1000)
            complete_event = PostProcessingCompleteEvent(
                experiment_id=experiment_id,
                tasks_completed=steps_completed,
                tasks_failed=steps_failed,
                duration_ms=duration_ms,
            )
            await self.experiment_event_bus.emit(complete_event)
            
            # Update manifest back to completed status
            manifest.update_experiment_status(ExperimentStatus.COMPLETED)
            
        except Exception as e:
            # Display error in a nice panel
            error_message = "Import/Transcript Generation Failed\n\n"
            error_message += f"Experiment: {experiment_id}\n\n"
            error_message += f"Error: {str(e)}"

            # Add helpful context based on error type
            context = None
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                context = (
                    "This appears to be a database schema issue.\n"
                    "The database may need to be updated to match the current schema."
                )
            elif "permission" in str(e).lower():
                context = "This appears to be a file permission issue."
            else:
                context = "Check the logs for more details."

            self.display.error(
                error_message, title="Import Error", context=context, use_panel=True
            )

            # Log but don't fail the experiment
            logging.error(
                f"Error during auto-import/transcript generation: {e}", exc_info=True
            )
            
            # Still emit complete event even if some tasks failed
            duration_ms = int((time.time() - start_time) * 1000)
            complete_event = PostProcessingCompleteEvent(
                experiment_id=experiment_id,
                tasks_completed=steps_completed,
                tasks_failed=steps_failed + ["Unknown"],  # Add unknown for the exception
                duration_ms=duration_ms,
            )
            await self.experiment_event_bus.emit(complete_event)
            
            # Update manifest back to completed status even if some tasks failed
            manifest.update_experiment_status(ExperimentStatus.COMPLETED)
