"""Handle all experiment setup tasks."""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..config.models import get_model_config
from ..core.types import Agent
from ..providers.api_key_manager import APIKeyManager
from ..providers.builder import build_provider as get_provider_for_model
from .config import ExperimentConfig
from .manifest import ManifestManager
from .tracking_event_bus import TrackingEventBus


class ExperimentSetup:
    """Handle all experiment setup tasks."""

    def create_manifest(
        self, exp_dir: Path, experiment_id: str, config: ExperimentConfig
    ) -> ManifestManager:
        """Create experiment manifest.

        Args:
            exp_dir: Experiment directory
            experiment_id: Unique experiment ID
            config: Experiment configuration

        Returns:
            ManifestManager instance
        """
        manifest = ManifestManager(exp_dir)
        manifest.create(
            experiment_id=experiment_id,
            name=config.name,
            config=config.dict(),
            total_conversations=config.repetitions,
        )
        return manifest

    def validate_api_keys(self, config: ExperimentConfig) -> None:
        """Validate API keys for all required providers.

        Args:
            config: Experiment configuration

        Raises:
            Exception: If API keys are missing or invalid
        """
        providers = set()
        agent_a_config = get_model_config(config.agent_a_model)
        agent_b_config = get_model_config(config.agent_b_model)

        if agent_a_config:
            providers.add(agent_a_config.provider)
        if agent_b_config:
            providers.add(agent_b_config.provider)

        # Check all providers have API keys before starting
        APIKeyManager.validate_required_providers(list(providers))

    async def setup_event_bus(
        self, exp_dir: Path, conversation_id: str
    ) -> TrackingEventBus:
        """Create and start tracking event bus for conversation.

        Args:
            exp_dir: Experiment directory
            conversation_id: Unique conversation ID

        Returns:
            Started TrackingEventBus instance
        """
        event_bus = TrackingEventBus(
            experiment_dir=exp_dir, conversation_id=conversation_id
        )
        await event_bus.start()
        return event_bus

    async def create_agents_and_providers(
        self, config: ExperimentConfig
    ) -> Tuple[Dict[str, Agent], Dict]:
        """Create agents and providers from configuration.

        Args:
            config: Experiment configuration

        Returns:
            Tuple of (agents dict, providers dict)

        Raises:
            ValueError: If model configuration is invalid or providers can't be created
        """
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

        logging.info("Providers created successfully")

        # Resolve thinking settings (think is global, think_a/think_b are overrides)
        # If think_a is explicitly set (True or False), use it; otherwise fall back to think
        thinking_a = config.think_a if config.think_a else config.think
        thinking_b = config.think_b if config.think_b else config.think

        # Create agents with display names from model config
        agent_a = Agent(
            id="agent_a",
            model=model_a_config.model_id,
            model_display_name=model_a_config.display_name,
            temperature=config.temperature_a,
            display_name=model_a_config.display_name,  # Use the model's display name
            thinking_enabled=thinking_a if thinking_a else None,
            thinking_budget=config.think_budget if thinking_a else None,
        )

        agent_b = Agent(
            id="agent_b",
            model=model_b_config.model_id,
            model_display_name=model_b_config.display_name,
            temperature=config.temperature_b,
            display_name=model_b_config.display_name,  # Use the model's display name
            thinking_enabled=thinking_b if thinking_b else None,
            thinking_budget=config.think_budget if thinking_b else None,
        )

        agents = {"agent_a": agent_a, "agent_b": agent_b}
        providers = {"agent_a": provider_a, "agent_b": provider_b}

        logging.info("Agents created successfully")

        return agents, providers

    def setup_output_and_console(
        self, config: ExperimentConfig, exp_dir: Path, conversation_id: str
    ) -> Tuple:
        """Set up output manager and console for display.

        Args:
            config: Experiment configuration
            exp_dir: Experiment directory
            conversation_id: Conversation ID

        Returns:
            Tuple of (output_manager, console)
        """
        # Create minimal output manager that returns the experiment directory
        from rich.console import Console

        from ..io.output_manager import OutputManager

        output_manager = OutputManager()

        # Override the create_conversation_dir to return the experiment directory
        def override_create_dir(conv_id: Optional[str]) -> tuple[str, Path]:
            return (conversation_id, exp_dir)

        output_manager.create_conversation_dir = override_create_dir  # type: ignore[assignment]

        # Check if we need a console for display modes
        console = None
        if config.display_mode in ["chat", "tail"]:
            console = Console()

        return output_manager, console
