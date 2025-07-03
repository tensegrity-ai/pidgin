# pidgin/experiments/runner.py
"""Experiment runner supporting both sequential and parallel execution."""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import uuid

from ..core import Conductor, EventBus
from ..core.events import (
    ConversationStartEvent,
    TurnCompleteEvent,
    ConversationEndEvent,
    MessageCompleteEvent,
    SystemPromptEvent
)
from ..core.types import Agent
from ..config.models import get_model_config
from ..io.output_manager import OutputManager
from ..database.event_store import EventStore
from .config import ExperimentConfig
from .event_handler import ExperimentEventHandler
from .daemon import ExperimentDaemon

# Import provider builder and prompt builder to avoid circular imports
from ..providers.builder import build_provider as get_provider_for_model
from ..config.prompts import build_initial_prompt
from ..config.resolution import resolve_temperatures, resolve_awareness_levels


# The functions are now imported above


class ExperimentRunner:
    """Runs experiment conversations with configurable parallelism."""
    
    def __init__(self, storage: Optional[EventStore] = None, 
                 daemon: Optional[ExperimentDaemon] = None):
        """Initialize experiment runner.
        
        Args:
            storage: Database storage instance
            daemon: Optional daemon instance for stop detection
        """
        self.storage = storage or EventStore()
        self.daemon = daemon
        self.active_tasks = {}
        self.completed_count = 0
        self.failed_count = 0
    
    async def run_experiment_with_id(self, experiment_id: str, config: ExperimentConfig):
        """Run experiment with existing ID.
        
        This is called by the daemon after it has already created the experiment record.
        
        Args:
            experiment_id: Existing experiment ID
            config: Experiment configuration
        """
        try:
            # Mark experiment as running in database
            await self.storage.update_experiment_status(experiment_id, 'running')
            
            # Prepare conversation configs
            conversations = []
            for i in range(config.repetitions):
                conv_id = f"conv_{experiment_id}_{uuid.uuid4().hex[:8]}"
                
                # Create conversation record
                conv_config = {
                    'agent_a_model': config.agent_a_model,
                    'agent_b_model': config.agent_b_model,
                    'initial_prompt': config.custom_prompt,
                    'max_turns': config.max_turns,
                    'temperature_a': config.temperature_a,
                    'temperature_b': config.temperature_b,
                    'first_speaker': config.first_speaker
                }
                
                await self.storage.create_conversation(experiment_id, conv_id, conv_config)
                conversations.append((conv_id, conv_config))
            
            # Run conversations with controlled parallelism
            await self._run_parallel_conversations(
                experiment_id, config, conversations
            )
            
            # Update final status
            if self.daemon and self.daemon.is_stopping():
                await self.storage.update_experiment_status(experiment_id, 'interrupted')
            else:
                await self.storage.update_experiment_status(experiment_id, 'completed')
                
        except Exception as e:
            logging.error(f"Experiment failed: {e}", exc_info=True)
            await self.storage.update_experiment_status(experiment_id, 'failed')
            raise
    
    async def _run_parallel_conversations(self,
                                        experiment_id: str,
                                        config: ExperimentConfig,
                                        conversations: List[Tuple[str, Dict]]):
        """Run conversations in parallel with rate limit awareness.
        
        Args:
            experiment_id: Experiment ID
            config: Experiment configuration
            conversations: List of (conversation_id, config) tuples
        """
        # Determine parallelism based on rate limits
        # Start conservative, can be tuned based on provider limits
        max_parallel = min(config.max_parallel, 5)  # Cap at 5 for safety
        
        logging.info(f"Running {len(conversations)} conversations with parallelism={max_parallel}")
        
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
                        experiment_id, conv_id, config, conv_config
                    )
                    self.completed_count += 1
                    logging.info(f"Completed {conv_id} ({self.completed_count}/{total})")
                    
                except asyncio.CancelledError:
                    # Handle graceful cancellation
                    logging.info(f"Cancelled {conv_id}")
                    raise
                except Exception as e:
                    self.failed_count += 1
                    logging.error(f"Failed {conv_id}: {e}", exc_info=True)
                    await self.storage.update_conversation_status(
                        conv_id, 'failed', error_message=str(e)
                    )
                    
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
                await asyncio.sleep(2.0)  # 2 second delay between starting conversations
            
        # Wait for all to complete or cancellation
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions that weren't already handled
            for i, result in enumerate(results):
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
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
    
    async def _run_single_conversation(self,
                                     experiment_id: str,
                                     conversation_id: str,
                                     config: ExperimentConfig,
                                     conv_config: Dict[str, Any]):
        """Run a single conversation with metrics capture.
        
        Args:
            experiment_id: Parent experiment ID
            conversation_id: Unique conversation ID
            config: Experiment configuration
            conv_config: Conversation-specific configuration
        """
        # Create isolated event bus for this conversation with shared storage
        event_bus = EventBus(self.storage)
        await event_bus.start()
        
        # Create event handler
        handler = ExperimentEventHandler(
            self.storage, 
            experiment_id, 
            event_bus
        )
        
        # Subscribe to events
        event_bus.subscribe(ConversationStartEvent, handler.handle_conversation_start)
        event_bus.subscribe(TurnCompleteEvent, handler.handle_turn_complete)
        event_bus.subscribe(ConversationEndEvent, handler.handle_conversation_end)
        event_bus.subscribe(MessageCompleteEvent, handler.handle_message_complete)
        event_bus.subscribe(SystemPromptEvent, handler.handle_system_prompt)
        
        # Build initial prompt using CLI logic
        initial_prompt = build_initial_prompt(
            custom_prompt=config.custom_prompt,
            dimensions=config.dimensions,
        )
        
        # Get model configs
        model_a_config = get_model_config(config.agent_a_model)
        model_b_config = get_model_config(config.agent_b_model)
        
        if not model_a_config or not model_b_config:
            raise ValueError(f"Invalid model configuration")
        
        # Create providers
        provider_a = await get_provider_for_model(
            config.agent_a_model,
            temperature=config.temperature_a
        )
        provider_b = await get_provider_for_model(
            config.agent_b_model,
            temperature=config.temperature_b
        )
        
        if not provider_a or not provider_b:
            raise ValueError("Failed to create providers")
        
        # Create agents
        agent_a = Agent(
            id="agent_a",
            model=model_a_config.model_id,
            model_shortname=config.agent_a_model,
            temperature=config.temperature_a
        )
        
        agent_b = Agent(
            id="agent_b", 
            model=model_b_config.model_id,
            model_shortname=config.agent_b_model,
            temperature=config.temperature_b
        )
        
        # Set up providers dict
        providers = {
            "agent_a": provider_a,
            "agent_b": provider_b
        }
        
        # Create output manager for this conversation
        output_manager = OutputManager()
        
        # Create conductor with the isolated event bus
        conductor = Conductor(
            base_providers=providers,
            output_manager=output_manager,
            console=None,  # No console output for experiments
            convergence_threshold_override=config.convergence_threshold,
            convergence_action_override=config.convergence_action,
            bus=event_bus  # Use conversation-specific bus
        )
        
        try:
            # Run the conversation
            await conductor.run_conversation(
                agent_a=agent_a,
                agent_b=agent_b,
                initial_prompt=initial_prompt,
                max_turns=config.max_turns,
                display_mode='quiet',  # Minimal output for experiments
                show_timing=False,
                choose_names=config.choose_names,
                awareness_a=config.awareness_a or config.awareness,
                awareness_b=config.awareness_b or config.awareness,
                temperature_a=config.temperature_a or config.temperature,
                temperature_b=config.temperature_b or config.temperature,
                conversation_id=conversation_id
            )

        finally:
            # Stop the event bus
            await event_bus.stop()
