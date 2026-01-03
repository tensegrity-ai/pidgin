"""Configuration management for Pidgin."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError
from rich.console import Console

from ..io.directories import get_config_dir
from ..io.logger import get_logger
from ..metrics.constants import (
    DEFAULT_CONVERGENCE_ACTION,
    DEFAULT_CONVERGENCE_PROFILE,
    DEFAULT_CONVERGENCE_THRESHOLD,
    DEFAULT_CONVERGENCE_WEIGHTS,
    ConvergenceComponents,
    ConvergenceProfiles,
)
from .schema import PidginConfig

logger = get_logger("config")


class Config:
    """Configuration manager for Pidgin."""

    # Use convergence profiles from constants
    CONVERGENCE_PROFILES = DEFAULT_CONVERGENCE_WEIGHTS

    DEFAULT_CONFIG = {
        "conversation": {
            "convergence_threshold": DEFAULT_CONVERGENCE_THRESHOLD,
            "convergence_action": DEFAULT_CONVERGENCE_ACTION,
            "convergence_profile": DEFAULT_CONVERGENCE_PROFILE,  # Now defaults
        },
        "ollama": {
            "auto_start": False,  # Require explicit consent or config
        },
        "convergence": {
            "profile": DEFAULT_CONVERGENCE_PROFILE,
            # Custom weights (used when profile is "custom")
            "custom_weights": DEFAULT_CONVERGENCE_WEIGHTS[ConvergenceProfiles.BALANCED],
        },
        "context_management": {
            "enabled": True,
            "warning_threshold": 80,  # Warn at 80% capacity
            "auto_pause_threshold": 95,  # Auto-pause at 95% capacity
            "show_usage": True,  # Display context usage in UI
        },
        "defaults": {
            "max_turns": 20,
            "manual_mode": False,
            "streaming_interrupts": False,  # Removed - using Ctrl+C signals instead
            "human_tag": "",  # Tag for human/researcher prompts (empty by default)
        },
        "experiments": {
            "unattended": {
                "convergence_threshold": 0.75,  # More aggressive
                "convergence_action": "stop",
            },
            "baseline": {"convergence_threshold": 1.0},  # Never stop on convergence
        },
        "providers": {
            "context_management": {
                "enabled": True,
                "context_reserve_ratio": 0.25,  # Reserve 25% for response
                "min_messages_retained": 10,  # Never go below this
                "truncation_strategy": "sliding_window",
                "safety_factor": 0.9,  # Use 90% of limits
            },
            "rate_limiting": {
                "enabled": True,
                "show_pacing_indicators": True,  # Show UI indicators when pacing
                "conservative_estimates": True,  # Overestimate tokens to be safe
                "safety_margin": 0.9,  # Use 90% of rate limits
                "token_estimation_multiplier": 1.1,  # Add 10% buffer
                "backoff_base_delay": 1.0,
                "backoff_max_delay": 60.0,
                "sliding_window_minutes": 1,  # Track over 1 minute
                "custom_limits": {
                    # Override default rate limits per provider
                    # "anthropic": {
                    #     "requests_per_minute": 45,
                    #     "tokens_per_minute": 35000,
                    # },
                },
            },
            "overrides": {
                # Per-provider overrides - uncomment to customize
                # "anthropic": {
                #     "tokens_per_minute": 400000,
                #     "context_limit": 180000,
                # },
                # "openai": {
                #     "tokens_per_minute": 150000,
                #     "context_limit": 120000,
                # },
                # "google": {
                #     "tokens_per_minute": 360000,
                #     "context_limit": 900000,
                # },
                # "xai": {
                #     "tokens_per_minute": 150000,
                #     "context_limit": 120000,
                # },
            },
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        # Validate default config
        try:
            validated_config = PidginConfig(**self.DEFAULT_CONFIG)  # type: ignore[arg-type]
            self.config = validated_config.model_dump()
        except ValidationError as e:
            # This should never happen with our defaults
            logger.error("Default configuration is invalid!")
            raise RuntimeError("Invalid default configuration") from e

        self.config_path = config_path

        # Only load from explicit path if provided
        if config_path:
            self.load_from_file(config_path)
        else:
            # Check standard location (but don't prompt)
            config_path = get_config_dir() / "pidgin.yaml"
            if config_path.exists():
                logger.debug(f"Loading config from: {config_path}")
                self.load_from_file(config_path)

    def _check_and_create_config(self):
        """Check for config file and offer to create one if missing."""
        config_path = get_config_dir() / "pidgin.yaml"

        if config_path.exists():
            logger.debug(f"Loading config from: {config_path}")
            self.load_from_file(config_path)
            return

        # No config found - ask if user wants to create one
        logger.warning("No configuration file found.")
        print("\nNo configuration file found.")
        print(f"Would you like to create one at: {config_path}?")
        print("This will let you customize convergence profiles and other settings.")

        console = Console()
        response = console.input("\nCreate config file? [y/N]: ")

        if response.lower() == "y":
            # Create directory if needed
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write example config
            self._write_example_config(config_path)
            logger.info(f"Created config at: {config_path}")
            print(f"\n✓ Created config at: {config_path}")
            print("You can edit this file to customize Pidgin's behavior.")

            # Load the newly created config
            self.load_from_file(config_path)
        else:
            logger.info("Using default configuration")

    def _write_example_config(self, path: Path):
        """Write example configuration file."""
        example_config = """# Pidgin configuration file
# Edit this file to customize behavior

conversation:
  convergence_threshold: 0.85    # Stop when convergence exceeds this (0.0-1.0)
  convergence_action: stop       # What to do: stop, warn, or continue
  convergence_profile: balanced  # Profile: balanced, structural, semantic, etc.

convergence:
  # Choose a built-in profile or use custom weights
  profile: structural  # Emphasizes structural similarity

  # Custom weights (used when profile is "custom", must sum to 1.0)
  custom_weights:
    content: 0.25      # Word/phrase similarity
    structure: 0.35    # Paragraphs, lists, questions
    sentences: 0.2     # Sentence patterns
    length: 0.1        # Message length similarity
    punctuation: 0.1   # Punctuation usage

context_management:
  enabled: true
  warning_threshold: 80   # Warn at 80% capacity
  auto_pause_threshold: 95  # Auto-pause at 95%
  show_usage: true

defaults:
  max_turns: 20
  manual_mode: false

ollama:
  auto_start: false  # Set to true to auto-start server without prompting

experiments:
  unattended:
    convergence_threshold: 0.75
    convergence_action: stop
  baseline:
    convergence_threshold: 1.0  # Never stop on convergence
"""
        with open(path, "w") as f:
            f.write(example_config)

    def load_from_file(self, path: Path):
        """Load configuration from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            user_config = yaml.safe_load(f)

        if user_config:
            # Merge with defaults first
            merged_config = self._deep_merge(self.config, user_config)

            # Validate the merged configuration
            try:
                validated_config = PidginConfig(**merged_config)
                # Convert back to dict for internal use
                self.config = validated_config.model_dump()
                self.config_path = path
            except ValidationError as e:
                logger.error(f"Configuration validation failed: {path}")
                print(f"\nError: Configuration validation failed: {path}")
                for err in e.errors():
                    field_path = " → ".join(str(loc) for loc in err["loc"])
                    print(f"  {field_path}: {err['msg']}")
                raise ValueError(f"Invalid configuration in {path}") from e

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'conversation.enabled')."""
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """Set config value using dot notation."""
        # Create a copy to validate
        test_config = self.config.copy()

        keys = key_path.split(".")
        config = test_config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value in test config
        config[keys[-1]] = value

        # Validate the entire config
        try:
            validated_config = PidginConfig(**test_config)
            # If valid, apply to actual config
            self.config = validated_config.model_dump()
        except ValidationError as e:
            # Find the relevant error for this field
            for err in e.errors():
                err_path = ".".join(str(loc) for loc in err["loc"])
                if err_path == key_path or err_path.startswith(key_path):
                    raise ValueError(
                        f"Invalid value for {key_path}: {err['msg']}"
                    ) from e
            # If no specific error found, raise general validation error
            raise ValueError(
                f"Configuration validation failed after setting {key_path}"
            ) from e

    def save(self, path: Optional[Path] = None):
        """Save configuration to file."""
        save_path = path or self.config_path
        if not save_path:
            save_path = Path.cwd() / "pidgin.yaml"

        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def get_convergence_config(self) -> Dict[str, Any]:
        """Get convergence configuration including weights."""
        conv_config = self.get("conversation", {}).copy()

        # Add convergence weights based on profile
        profile = self.get("convergence.profile", DEFAULT_CONVERGENCE_PROFILE)
        if profile == ConvergenceProfiles.CUSTOM:
            weights = self.get(
                "convergence.custom_weights",
                self.CONVERGENCE_PROFILES[ConvergenceProfiles.BALANCED],
            )
            # Validate custom weights
            self._validate_convergence_weights(weights)
            conv_config["weights"] = weights
        else:
            conv_config["weights"] = self.CONVERGENCE_PROFILES.get(
                profile, self.CONVERGENCE_PROFILES[DEFAULT_CONVERGENCE_PROFILE]
            )
        conv_config["profile"] = profile

        return conv_config

    def _validate_convergence_weights(self, weights: Dict[str, float]) -> None:
        """Validate that convergence weights sum to 1.0.

        Args:
            weights: Dictionary of convergence component weights

        Raises:
            ValueError: If weights don't sum to 1.0 or are missing components
        """
        # Check all required components are present
        required_components = {
            ConvergenceComponents.CONTENT,
            ConvergenceComponents.STRUCTURE,
            ConvergenceComponents.SENTENCES,
            ConvergenceComponents.LENGTH,
            ConvergenceComponents.PUNCTUATION,
        }

        weight_keys = set(weights.keys())
        if weight_keys != required_components:
            missing = required_components - weight_keys
            extra = weight_keys - required_components
            msg = []
            if missing:
                msg.append(f"Missing components: {', '.join(missing)}")
            if extra:
                msg.append(f"Unknown components: {', '.join(extra)}")
            raise ValueError(f"Invalid convergence weights. {' '.join(msg)}")

        # Check weights sum to 1.0
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(
                f"Convergence weights must sum to 1.0, but got {total:.3f}. "
                f"Current weights: {weights}"
            )

    def get_context_config(self) -> Dict[str, Any]:
        """Get context management configuration."""
        return self.get("context_management", {})

    def get_provider_config(self) -> Dict[str, Any]:
        """Get provider configuration."""
        return self.get("providers", {})

    def apply_experiment_profile(self, profile: str):
        """Apply an experiment profile to current config."""
        if profile_config := self.get(f"experiments.{profile}"):
            self.config = self._deep_merge(
                self.config, {"conversation": profile_config}
            )

    def to_dict(self) -> Dict[str, Any]:
        """Return the full configuration as a dictionary."""
        return self.config.copy()
