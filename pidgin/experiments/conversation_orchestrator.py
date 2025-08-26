"""Orchestrate conversation execution."""

from pathlib import Path
from typing import Dict, Optional

from ..config.prompts import build_initial_prompt
from ..core.app_context import AppContext
from ..core.conductor import Conductor
from ..core.events import ConversationBranchedEvent
from .config import ExperimentConfig
from .daemon import ExperimentDaemon
from .manifest import ManifestManager
from .tracking_event_bus import TrackingEventBus


class ConversationOrchestrator:
    """Orchestrate conversation execution."""

    def __init__(
        self, app_context: AppContext, daemon: Optional[ExperimentDaemon] = None
    ):
        """Initialize conversation orchestrator.

        Args:
            app_context: Application context with dependencies
            daemon: Optional daemon instance for stop detection
        """
        self.app_context = app_context
        self.daemon = daemon

    def register_conversation(self, exp_dir: Path, conversation_id: str) -> None:
        """Register a new conversation in the manifest.

        Args:
            exp_dir: Experiment directory
            conversation_id: Unique conversation ID
        """
        manifest = ManifestManager(exp_dir)
        jsonl_filename = f"events_{conversation_id}.jsonl"
        manifest.add_conversation(conversation_id, jsonl_filename)

    async def create_and_run_conductor(
        self,
        config: ExperimentConfig,
        agents: Dict,
        providers: Dict,
        output_manager,
        console,
        event_bus: TrackingEventBus,
        conversation_id: str,
        experiment_id: Optional[str] = None,
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
        initial_prompt = build_initial_prompt(custom_prompt=config.custom_prompt)

        # Create conductor with the isolated event bus
        conductor = Conductor(
            output_manager=output_manager,
            config=self.app_context.config,
            token_tracker=self.app_context.token_tracker,
            base_providers=providers,
            console=console,
            convergence_threshold_override=config.convergence_threshold,
            convergence_action_override=config.convergence_action,
            bus=event_bus,
        )

        # Display mode is handled by the setup, not needed here

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
            experiment_id=experiment_id,
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
        experiment_id: Optional[str] = None,
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
                    source_conversation_id=branch_from,
                    conversation_id=conversation_id,
                    branch_point=branch_at,
                    parameter_changes={},  # Add required field
                    experiment_id=experiment_id,
                )
            )

            # Build initial prompt for branching
            initial_prompt = build_initial_prompt(
                custom_prompt=config.custom_prompt,
            )

            # Create conductor for branched conversation
            conductor = Conductor(
                output_manager=output_manager,
                config=self.app_context.config,
                token_tracker=self.app_context.token_tracker,
                base_providers=providers,
                console=console,
                convergence_threshold_override=config.convergence_threshold,
                convergence_action_override=config.convergence_action,
                bus=event_bus,
            )

            # Display mode is handled by the setup, not needed here

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
                experiment_id=experiment_id,
            )
        else:
            await self.create_and_run_conductor(
                config=config,
                agents=agents,
                providers=providers,
                output_manager=output_manager,
                console=console,
                event_bus=event_bus,
                conversation_id=conversation_id,
                experiment_id=experiment_id,
            )
