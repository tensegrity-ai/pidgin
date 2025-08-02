"""Orchestrate conversation execution."""

import logging
from pathlib import Path
from typing import Dict, Optional

from ..config.prompts import build_initial_prompt
from ..core.conductor import Conductor
from ..core.events import ConversationBranchedEvent
from .config import ExperimentConfig
from .daemon import ExperimentDaemon
from .manifest import ManifestManager
from .tracking_event_bus import TrackingEventBus


class ConversationOrchestrator:
    """Orchestrate conversation execution."""

    def __init__(self, daemon: Optional[ExperimentDaemon] = None):
        """Initialize conversation orchestrator.
        
        Args:
            daemon: Optional daemon instance for stop detection
        """
        self.daemon = daemon

    def register_conversation(self, exp_dir: Path, conversation_id: str) -> None:
        """Register a new conversation in the manifest.
        
        Args:
            exp_dir: Experiment directory
            conversation_id: Unique conversation ID
        """
        manifest = ManifestManager(exp_dir)
        manifest.add_conversation(conversation_id)

    async def create_and_run_conductor(
        self,
        config: ExperimentConfig,
        agents: Dict,
        providers: Dict,
        output_manager,
        console,
        event_bus: TrackingEventBus,
        conversation_id: str,
    ) -> None:
        """Create conductor and run the conversation.
        
        Args:
            config: Experiment configuration
            agents: Dictionary of agents
            providers: Dictionary of providers
            output_manager: Output manager instance
            console: Console instance for display
            event_bus: Event bus for tracking
            conversation_id: Unique conversation ID
        """
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

        # Set display mode on the conductor
        conductor.display_mode = config.display_mode

        # Run conversation with daemon stop detection
        await conductor.run_conversation(
            agents=agents,
            initial_prompt=initial_prompt,
            first_speaker=config.first_speaker,
            max_turns=config.max_turns,
            daemon=self.daemon,
        )

    async def handle_branching(
        self,
        config: ExperimentConfig,
        agents: Dict,
        providers: Dict,
        output_manager,
        console,
        event_bus: TrackingEventBus,
        conversation_id: str,
        branch_from: Optional[str] = None,
        branch_at: Optional[int] = None,
    ) -> None:
        """Handle conversation branching if configured.
        
        Args:
            config: Experiment configuration
            agents: Dictionary of agents
            providers: Dictionary of providers
            output_manager: Output manager instance
            console: Console instance for display
            event_bus: Event bus for tracking
            conversation_id: Unique conversation ID
            branch_from: ID of conversation to branch from
            branch_at: Turn number to branch at
        """
        # Check for branching
        if branch_from and branch_at is not None:
            # Emit branch event
            await event_bus.emit(
                ConversationBranchedEvent(
                    parent_conversation_id=branch_from,
                    branch_conversation_id=conversation_id,
                    branch_point=branch_at,
                )
            )

            # Build initial prompt for branching
            initial_prompt = build_initial_prompt(
                custom_prompt=config.custom_prompt,
                dimensions=config.dimensions,
            )

            # Create conductor for branched conversation
            conductor = Conductor(
                base_providers=providers,
                output_manager=output_manager,
                console=console,
                convergence_threshold_override=config.convergence_threshold,
                convergence_action_override=config.convergence_action,
                bus=event_bus,
            )

            # Set display mode
            conductor.display_mode = config.display_mode

            # Run branched conversation
            await conductor.run_branched_conversation(
                agents=agents,
                branch_from_conversation_id=branch_from,
                branch_at_turn=branch_at,
                initial_prompt=initial_prompt,
                first_speaker=config.first_speaker,
                max_turns=config.max_turns,
                daemon=self.daemon,
            )
        else:
            # Run normal conversation
            await self.create_and_run_conductor(
                config=config,
                agents=agents,
                providers=providers,
                output_manager=output_manager,
                console=console,
                event_bus=event_bus,
                conversation_id=conversation_id,
            )