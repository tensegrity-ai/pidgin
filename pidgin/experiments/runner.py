"""Experiment runner for serial conversation execution."""

import os
import asyncio
import uuid
from typing import Optional, Dict, Any
from pathlib import Path
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
from ..providers.anthropic import AnthropicProvider
from ..providers.openai import OpenAIProvider
from ..providers.google import GoogleProvider
from ..providers.xai import xAIProvider
from ..config.models import get_model_config
from ..ui.display_filter import DisplayFilter
from ..io.output_manager import OutputManager
from .storage import ExperimentStore
from .config import ExperimentConfig
from .event_handler import ExperimentEventHandler


class ExperimentRunner:
    """Runs experiments by orchestrating conversations."""
    
    def __init__(self, storage: Optional[ExperimentStore] = None):
        """Initialize experiment runner.
        
        Args:
            storage: Database storage instance (creates default if None)
        """
        self.storage = storage or ExperimentStore()
    
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
                    print(f"Error in conversation {conv_id}: {str(e)}")
                    self.storage.update_conversation_status(
                        conv_id, 'failed', error_message=str(e)
                    )
                
                # Small delay between conversations to avoid rate limits
                if i < config.repetitions - 1:
                    await asyncio.sleep(1.0)
            
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
        # Create event bus and handler
        event_bus = EventBus()
        handler = ExperimentEventHandler(self.storage, experiment_id)
        
        # Subscribe to events
        event_bus.subscribe(ConversationStartEvent, handler.handle_conversation_start)
        event_bus.subscribe(TurnCompleteEvent, handler.handle_turn_complete)
        event_bus.subscribe(ConversationEndEvent, handler.handle_conversation_end)
        event_bus.subscribe(MessageCompleteEvent, handler.handle_message_complete)
        event_bus.subscribe(SystemPromptEvent, handler.handle_system_prompt)
        
        # Get providers
        providers = await self._get_providers(config)
        
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
        
        # Create agents
        agent_a = Agent(
            id="agent_a",
            name=config.agent_a_model,
            model=config.agent_a_model
        )
        agent_b = Agent(
            id="agent_b", 
            name=config.agent_b_model,
            model=config.agent_b_model
        )
        
        # Create conductor
        conductor = Conductor(
            providers=providers,
            output_manager=output_manager,
            console=None  # No console output for experiments
        )
        
        # Set convergence threshold if specified
        if config.convergence_threshold is not None:
            conductor.convergence_threshold = config.convergence_threshold
            conductor.convergence_action = config.convergence_action
        
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
        
        # Run the conversation
        await conductor.run_conversation(
            agent_a=agent_a,
            agent_b=agent_b,
            initial_prompt=config.initial_prompt,
            max_turns=config.max_turns,
            display_mode='quiet',  # Minimal output
            show_timing=False,
            choose_names=config.choose_names,
            awareness_a=config.awareness_a,
            awareness_b=config.awareness_b,
            temperature_a=config.temperature_a,
            temperature_b=config.temperature_b
        )
    
    async def _get_providers(self, config: ExperimentConfig) -> Dict[str, Any]:
        """Get provider instances for the models."""
        providers = {}
        
        # Get model configs
        model_a_config = get_model_config(config.agent_a_model)
        model_b_config = get_model_config(config.agent_b_model)
        
        if not model_a_config:
            raise ValueError(f"Unknown model: {config.agent_a_model}")
        if not model_b_config:
            raise ValueError(f"Unknown model: {config.agent_b_model}")
        
        # Create providers for each agent
        if model_a_config.provider == "anthropic":
            providers['agent_a'] = AnthropicProvider(config.agent_a_model)
        elif model_a_config.provider == "openai":
            providers['agent_a'] = OpenAIProvider(config.agent_a_model)
        elif model_a_config.provider == "google":
            providers['agent_a'] = GoogleProvider(config.agent_a_model)
        elif model_a_config.provider == "xai":
            providers['agent_a'] = xAIProvider(config.agent_a_model)
        else:
            raise ValueError(f"Unknown provider: {model_a_config.provider}")
            
        if model_b_config.provider == "anthropic":
            providers['agent_b'] = AnthropicProvider(config.agent_b_model)
        elif model_b_config.provider == "openai":
            providers['agent_b'] = OpenAIProvider(config.agent_b_model)
        elif model_b_config.provider == "google":
            providers['agent_b'] = GoogleProvider(config.agent_b_model)
        elif model_b_config.provider == "xai":
            providers['agent_b'] = xAIProvider(config.agent_b_model)
        else:
            raise ValueError(f"Unknown provider: {model_b_config.provider}")
        
        return providers