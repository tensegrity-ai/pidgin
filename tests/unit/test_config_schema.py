"""Tests for configuration schema validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from pidgin.config.config import Config
from pidgin.config.schema import (
    ConvergenceWeights,
    ConversationConfig,
    PidginConfig,
    ProviderRateLimit,
    RateLimitingConfig,
)


class TestConfigSchema:
    """Test configuration schema validation."""

    def test_valid_default_config(self):
        """Test that default configuration is valid."""
        config = Config()
        assert config.config is not None
        # Should not raise any validation errors

    def test_convergence_weights_validation(self):
        """Test convergence weights validation."""
        # Valid weights
        weights = ConvergenceWeights(
            content=0.4, structure=0.15, sentences=0.2, length=0.15, punctuation=0.1
        )
        assert weights.content == 0.4

        # Invalid: weights don't sum to 1.0
        with pytest.raises(ValidationError) as exc_info:
            ConvergenceWeights(
                content=0.5,
                structure=0.2,
                sentences=0.2,
                length=0.2,
                punctuation=0.2,  # Sum = 1.3
            )
        assert "sum to 1.0" in str(exc_info.value)

        # Invalid: negative weight
        with pytest.raises(ValidationError) as exc_info:
            ConvergenceWeights(
                content=-0.1, structure=0.3, sentences=0.3, length=0.3, punctuation=0.2
            )
        assert "greater than or equal to 0" in str(exc_info.value)

        # Invalid: weight > 1
        with pytest.raises(ValidationError) as exc_info:
            ConvergenceWeights(
                content=1.5, structure=0.0, sentences=0.0, length=0.0, punctuation=0.0
            )
        assert "less than or equal to 1" in str(exc_info.value)

    def test_conversation_config_validation(self):
        """Test conversation configuration validation."""
        # Valid config
        config = ConversationConfig(
            convergence_threshold=0.85,
            convergence_action="stop",
            convergence_profile="balanced",
        )
        assert config.convergence_threshold == 0.85

        # Invalid: threshold out of range
        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(convergence_threshold=1.5)
        assert "less than or equal to 1" in str(exc_info.value)

        # Invalid: invalid action
        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(convergence_action="invalid")
        assert "Input should be 'stop' or 'warn'" in str(exc_info.value)

    def test_rate_limiting_config_validation(self):
        """Test rate limiting configuration validation."""
        # Valid config
        config = RateLimitingConfig(
            enabled=True,
            safety_margin=0.9,
            token_estimation_multiplier=1.1,
            backoff_base_delay=1.0,
            backoff_max_delay=60.0,
        )
        assert config.safety_margin == 0.9

        # Invalid: safety margin > 1
        with pytest.raises(ValidationError) as exc_info:
            RateLimitingConfig(safety_margin=1.5)
        assert "less than or equal to 1" in str(exc_info.value)

        # Invalid: negative delay
        with pytest.raises(ValidationError) as exc_info:
            RateLimitingConfig(backoff_base_delay=-1.0)
        assert "greater than 0" in str(exc_info.value)

        # Invalid: token multiplier < 1
        with pytest.raises(ValidationError) as exc_info:
            RateLimitingConfig(token_estimation_multiplier=0.5)
        assert "greater than 1" in str(exc_info.value)

    def test_provider_rate_limit_validation(self):
        """Test provider rate limit validation."""
        # Valid rate limit
        limit = ProviderRateLimit(requests_per_minute=60, tokens_per_minute=90000)
        assert limit.requests_per_minute == 60

        # Invalid: zero requests
        with pytest.raises(ValidationError) as exc_info:
            ProviderRateLimit(requests_per_minute=0, tokens_per_minute=1000)
        assert "greater than 0" in str(exc_info.value)

    def test_config_set_validation(self):
        """Test validation when setting config values."""
        config = Config()

        # Valid set
        config.set("conversation.convergence_threshold", 0.9)
        assert config.get("conversation.convergence_threshold") == 0.9

        # Invalid: threshold out of range
        with pytest.raises(ValueError) as exc_info:
            config.set("conversation.convergence_threshold", 1.5)
        assert "Invalid value" in str(exc_info.value)

        # Invalid: wrong type
        with pytest.raises(ValueError) as exc_info:
            config.set("conversation.convergence_threshold", "not a number")
        assert "Invalid value" in str(exc_info.value)

        # Invalid: invalid convergence action
        with pytest.raises(ValueError) as exc_info:
            config.set("conversation.convergence_action", "invalid_action")
        assert "Invalid value" in str(exc_info.value)

    def test_nested_config_validation(self):
        """Test validation of nested configuration."""
        config = Config()

        # Set valid nested value
        config.set("providers.rate_limiting.safety_margin", 0.8)
        assert config.get("providers.rate_limiting.safety_margin") == 0.8

        # Invalid nested value
        with pytest.raises(ValueError) as exc_info:
            config.set("providers.rate_limiting.safety_margin", 2.0)
        assert "Invalid value" in str(exc_info.value)

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for backward compatibility."""
        # Create config with extra fields
        config_dict = PidginConfig().model_dump()
        config_dict["extra_field"] = "extra_value"
        config_dict["conversation"]["extra_nested"] = 123

        # Should not raise validation error
        validated = PidginConfig(**config_dict)
        assert validated is not None

    def test_partial_config_merging(self, tmp_path):
        """Test that partial configs merge correctly with defaults."""
        # Create a minimal config file
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
conversation:
  convergence_threshold: 0.95
"""
        )

        # Load config
        config = Config(config_path=config_file)

        # Should have the overridden value
        assert config.get("conversation.convergence_threshold") == 0.95

        # Should still have default values for unspecified fields
        assert config.get("conversation.convergence_action") == "stop"
        assert config.get("defaults.max_turns") == 20

    def test_invalid_yaml_config(self, tmp_path):
        """Test loading invalid YAML configuration."""
        # Create an invalid config file
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text(
            """
conversation:
  convergence_threshold: 2.0  # Invalid: > 1.0
  convergence_action: invalid_action  # Invalid: not stop/warn
"""
        )

        # Should raise validation error
        with pytest.raises(ValueError) as exc_info:
            Config(config_path=config_file)
        assert "Invalid configuration" in str(exc_info.value)
