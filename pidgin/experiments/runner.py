# pidgin/experiments/runner.py
"""Experiment runner supporting both sequential and parallel execution."""

import os
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import uuid
from datetime import datetime

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
from .config import ExperimentConfig
from .daemon import ExperimentDaemon
from .manifest import ManifestManager
from .tracking_event_bus import TrackingEventBus

# Import provider builder and prompt builder to avoid circular imports
from ..providers.builder import build_provider as get_provider_for_model
from ..config.prompts import build_initial_prompt
from ..config.resolution import resolve_temperatures, resolve_awareness_levels


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
        exp_dir = self.output_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create manifest
        manifest = ManifestManager(exp_dir)
        manifest.create(
            experiment_id=experiment_id,
            name=config.name,
            config=config.dict(),
            total_conversations=config.repetitions
        )
        
        # Also write legacy metadata.json for backward compatibility
        metadata = {
            'experiment_id': experiment_id,
            'name': config.name,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'total_conversations': config.repetitions,
            'completed_conversations': 0,
            'failed_conversations': 0,
            'config': config.dict()
        }
        
        metadata_path = exp_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        try:
            
            # Prepare conversation configs
            conversations = []
            for i in range(config.repetitions):
                conv_id = f"conv_{experiment_id}_{uuid.uuid4().hex[:8]}"
                
                # Create conversation config
                conv_config = {
                    'conversation_id': conv_id,
                    'agent_a_model': config.agent_a_model,
                    'agent_b_model': config.agent_b_model,
                    'initial_prompt': config.custom_prompt,
                    'max_turns': config.max_turns,
                    'temperature_a': config.temperature_a,
                    'temperature_b': config.temperature_b,
                    'first_speaker': config.first_speaker
                }
                
                conversations.append((conv_id, conv_config))
            
            # Run conversations with controlled parallelism
            await self._run_parallel_conversations(
                experiment_id, config, conversations, exp_dir
            )
            
            # Update final status
            if self.daemon and self.daemon.is_stopping():
                final_status = 'interrupted'
            else:
                final_status = 'completed'
            
            # Update manifest with final status
            manifest.update_experiment_status(final_status)
            
            # Update legacy metadata
            metadata['status'] = final_status
            metadata['completed_at'] = datetime.utcnow().isoformat()
            metadata['completed_conversations'] = self.completed_count
            metadata['failed_conversations'] = self.failed_count
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logging.info(f"Experiment {experiment_id} completed with status: {final_status}")
                
        except Exception as e:
            logging.error(f"Experiment failed: {e}", exc_info=True)
            
            # Update manifest with error status
            manifest.update_experiment_status('failed', error=str(e))
            
            # Update legacy metadata
            metadata['status'] = 'failed'
            metadata['completed_at'] = datetime.utcnow().isoformat()
            metadata['error'] = str(e)
            metadata['completed_conversations'] = self.completed_count
            metadata['failed_conversations'] = self.failed_count
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            raise
    
    async def _run_parallel_conversations(self,
                                        experiment_id: str,
                                        config: ExperimentConfig,
                                        conversations: List[Tuple[str, Dict]],
                                        exp_dir: Path):
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
                        experiment_id, conv_id, config, conv_config, exp_dir
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
                    
                    # Write error to conversation metadata
                    conv_metadata = {
                        'conversation_id': conv_id,
                        'status': 'failed',
                        'error': str(e),
                        'failed_at': datetime.utcnow().isoformat()
                    }
                    
                    conv_metadata_path = exp_dir / f"{conv_id}_metadata.json"
                    with open(conv_metadata_path, 'w') as f:
                        json.dump(conv_metadata, f, indent=2)
                    
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
                                     conv_config: Dict[str, Any],
                                     exp_dir: Path):
        """Run a single conversation with metrics capture.
        
        Args:
            experiment_id: Parent experiment ID
            conversation_id: Unique conversation ID
            config: Experiment configuration
            conv_config: Conversation-specific configuration
        """
        # Register conversation in manifest first
        manifest = ManifestManager(exp_dir)
        jsonl_filename = f"{conversation_id}_events.jsonl"
        manifest.add_conversation(conversation_id, jsonl_filename)
        
        # Create tracking event bus for this conversation
        event_bus = TrackingEventBus(
            experiment_dir=exp_dir,
            conversation_id=conversation_id
        )
        await event_bus.start()
        
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
        
        # Create minimal output manager that returns the experiment directory
        from ..io.output_manager import OutputManager
        output_manager = OutputManager()
        # Override the create_conversation_dir to return the experiment directory
        output_manager.create_conversation_dir = lambda conv_id: (conversation_id, exp_dir)
        
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
            # Write conversation start metadata
            conv_metadata = {
                'conversation_id': conversation_id,
                'experiment_id': experiment_id,
                'status': 'running',
                'started_at': datetime.utcnow().isoformat(),
                'config': conv_config
            }
            
            conv_metadata_path = exp_dir / f"{conversation_id}_metadata.json"
            with open(conv_metadata_path, 'w') as f:
                json.dump(conv_metadata, f, indent=2)
            
            # Run the conversation
            await conductor.run_conversation(
                agent_a=agent_a,
                agent_b=agent_b,
                initial_prompt=initial_prompt,
                max_turns=config.max_turns,
                display_mode='none',  # No display for experiments
                show_timing=False,
                choose_names=config.choose_names,
                awareness_a=config.awareness_a or config.awareness,
                awareness_b=config.awareness_b or config.awareness,
                temperature_a=config.temperature_a or config.temperature,
                temperature_b=config.temperature_b or config.temperature,
                conversation_id=conversation_id
            )
            
            # Update conversation metadata with completion
            conv_metadata['status'] = 'completed'
            conv_metadata['completed_at'] = datetime.utcnow().isoformat()
            
            with open(conv_metadata_path, 'w') as f:
                json.dump(conv_metadata, f, indent=2)

        finally:
            # Stop the event bus
            await event_bus.stop()
