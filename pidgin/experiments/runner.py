"""Experiment runner for serial conversation execution."""

import os
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

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
from .storage import ExperimentStore
from .config import ExperimentConfig
from .event_handler import ExperimentEventHandler

# Import CLI functions for consistency
from ..cli import get_provider_for_model, _build_initial_prompt


class ExperimentRunner:
    """Runs experiments by orchestrating conversations."""
    
    def __init__(self, storage: Optional[ExperimentStore] = None, event_bus: Optional[EventBus] = None):
        """Initialize experiment runner.
        
        Args:
            storage: Database storage instance (creates default if None)
            event_bus: Optional shared EventBus for dashboard integration
        """
        self.storage = storage or ExperimentStore()
        self.event_bus = event_bus  # Will be None for normal operation
    
    async def run_experiment(self, config: ExperimentConfig) -> str:
        """Run all conversations for an experiment.
        
        Args:
            config: Experiment configuration
            
        Returns:
            experiment_id: The ID of the created experiment
        """
        # Validate config
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")
        
        # Create experiment record
        experiment_id = self.storage.create_experiment(config.name, config.dict())
        
        # Update experiment status to running
        self.storage.update_experiment_status(experiment_id, 'running')
        
        try:
            # Run conversations serially (Phase 2)
            for i in range(config.repetitions):
                conv_id = f"{experiment_id}_conv_{i:04d}"
                
                # Get config for this specific conversation
                conv_config = config.get_conversation_config(i)
                
                # Create conversation record
                self.storage.create_conversation(experiment_id, conv_id, conv_config)
                
                try:
                    # Run the conversation
                    await self._run_single_conversation(
                        experiment_id, conv_id, config, conv_config
                    )
                except Exception as e:
                    # Log error and continue with next conversation
                    # Error is already logged to storage, no need for print
                    self.storage.update_conversation_status(
                        conv_id, 'failed', error_message=str(e)
                    )
                
                # Delay between conversations to avoid rate limits
                if i < config.repetitions - 1:
                    await asyncio.sleep(5.0)  # 5 seconds between conversations
            
            # Update experiment status to completed
            self.storage.update_experiment_status(experiment_id, 'completed')
            
        except Exception as e:
            # Update experiment status to failed
            self.storage.update_experiment_status(experiment_id, 'failed')
            raise
        
        return experiment_id
    
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
        # Use shared event bus if available, otherwise create local one
        if self.event_bus:
            event_bus = self.event_bus
            print(f"[DEBUG] Using shared EventBus for conversation {conversation_id}")
        else:
            event_bus = EventBus()
            await event_bus.start()
            
        handler = ExperimentEventHandler(self.storage, experiment_id)
        
        # Subscribe to events
        event_bus.subscribe(ConversationStartEvent, handler.handle_conversation_start)
        event_bus.subscribe(TurnCompleteEvent, handler.handle_turn_complete)
        event_bus.subscribe(ConversationEndEvent, handler.handle_conversation_end)
        event_bus.subscribe(MessageCompleteEvent, handler.handle_message_complete)
        event_bus.subscribe(SystemPromptEvent, handler.handle_system_prompt)
        
        # Build initial prompt using CLI logic
        initial_prompt = _build_initial_prompt(
            custom_prompt=config.custom_prompt,
            dimensions=config.dimensions,
        )
        
        # Get model configs
        model_a_config = get_model_config(config.agent_a_model)
        model_b_config = get_model_config(config.agent_b_model)
        
        if not model_a_config:
            raise ValueError(f"Unknown model: {config.agent_a_model}")
        if not model_b_config:
            raise ValueError(f"Unknown model: {config.agent_b_model}")
        
        # Get providers using CLI function
        providers_map = {}
        provider_a = get_provider_for_model(config.agent_a_model)
        provider_b = get_provider_for_model(config.agent_b_model)
        
        # Map providers by model ID (matching CLI behavior)
        providers_map[model_a_config.model_id] = provider_a
        providers_map[model_b_config.model_id] = provider_b
        
        # Create output manager (minimal output for experiments)
        # Check if we're in a daemon context
        project_base = os.environ.get('PIDGIN_PROJECT_BASE')
        if project_base:
            # Use the preserved project base path
            base_dir = Path(project_base) / "pidgin_output"
        else:
            # Normal operation - resolve relative to current directory
            base_dir = Path("./pidgin_output").resolve()
        
        # Create a custom output manager that will use our conversation ID
        class ExperimentOutputManager(OutputManager):
            def __init__(self, base_dir, conv_id, conv_dir):
                super().__init__(base_dir)
                self._conv_id = conv_id
                self._conv_dir = conv_dir
                
            def create_conversation_dir(self):
                # Return our pre-determined conversation ID and directory
                self._conv_dir.mkdir(parents=True, exist_ok=True)
                return self._conv_id, self._conv_dir
        
        output_dir = base_dir / "experiments" / experiment_id / conversation_id
        output_manager = ExperimentOutputManager(str(base_dir), conversation_id, output_dir)
        
        # Determine temperatures (matching CLI logic)
        if config.temperature is not None:
            # --temperature sets both
            temperature_a = temperature_b = config.temperature
        else:
            # Use individual settings or None
            temperature_a = config.temperature_a
            temperature_b = config.temperature_b
        
        # Create agents with temperature settings
        agent_a = Agent(
            id="agent_a",
            name=model_a_config.shortname,
            model=model_a_config.model_id,
            temperature=temperature_a
        )
        agent_b = Agent(
            id="agent_b", 
            name=model_b_config.shortname,
            model=model_b_config.model_id,
            temperature=temperature_b
        )
        
        # Create conductor with convergence settings and shared EventBus
        conductor = Conductor(
            providers=providers_map,
            output_manager=output_manager,
            console=None,  # No console output for experiments
            convergence_threshold=config.convergence_threshold,
            convergence_action=config.convergence_action,
            event_bus=event_bus if self.event_bus else None,  # PASS THE SHARED BUS!
        )
        
        # Monkey patch the conductor to subscribe our handler to events
        original_init_event_system = conductor._initialize_event_system
        
        async def patched_init_event_system(conv_dir, display_mode, show_timing, agents):
            # Call the original method
            await original_init_event_system(conv_dir, display_mode, show_timing, agents)
            
            # Now subscribe our experiment handler to the events
            conductor.bus.subscribe(ConversationStartEvent, handler.handle_conversation_start)
            conductor.bus.subscribe(TurnCompleteEvent, handler.handle_turn_complete)
            conductor.bus.subscribe(ConversationEndEvent, handler.handle_conversation_end)
            conductor.bus.subscribe(MessageCompleteEvent, handler.handle_message_complete)
            conductor.bus.subscribe(SystemPromptEvent, handler.handle_system_prompt)
            
            # Also set the conversation ID in the handler
            handler.conversation_id = conversation_id
        
        conductor._initialize_event_system = patched_init_event_system
        
        # Determine actual awareness levels (matching CLI logic)
        actual_awareness_a = config.awareness_a if config.awareness_a else config.awareness
        actual_awareness_b = config.awareness_b if config.awareness_b else config.awareness
        
        # Run the conversation
        await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt=initial_prompt,
            max_turns=config.max_turns,
            display_mode='quiet',  # Minimal output
            show_timing=False,
            choose_names=config.choose_names,
            awareness_a=actual_awareness_a,
            awareness_b=actual_awareness_b,
            temperature_a=temperature_a,
            temperature_b=temperature_b
        )
    
