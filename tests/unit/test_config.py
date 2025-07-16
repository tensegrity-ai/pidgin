"""Tests for Config class functionality."""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import yaml
from pydantic import ValidationError

from pidgin.config.config import Config, get_config, load_config
from pidgin.constants import (
    DEFAULT_CONVERGENCE_ACTION,
    DEFAULT_CONVERGENCE_PROFILE,
    DEFAULT_CONVERGENCE_THRESHOLD,
    DEFAULT_CONVERGENCE_WEIGHTS,
    ConvergenceComponents,
    ConvergenceProfiles,
)


class TestConfig:
    """Test Config class functionality."""

    def test_init_with_defaults(self):
        """Test initialization with default configuration."""
        config = Config()

        # Check that defaults are loaded
        assert (
            config.get("conversation.convergence_threshold")
            == DEFAULT_CONVERGENCE_THRESHOLD
        )
        assert (
            config.get("conversation.convergence_action") == DEFAULT_CONVERGENCE_ACTION
        )
        assert config.get("defaults.max_turns") == 20
        assert config.get("context_management.enabled") is True
        assert config.config_path is None

    def test_init_with_nonexistent_path(self):
        """Test initialization with nonexistent config path."""
        nonexistent_path = Path("/nonexistent/config.yaml")

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            Config(config_path=nonexistent_path)

    def test_init_with_existing_standard_config(self, tmp_path):
        """Test initialization that finds standard config location."""
        # Create a standard config location
        config_dir = tmp_path / ".config" / "pidgin"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "pidgin.yaml"

        config_content = {"conversation": {"convergence_threshold": 0.95}}
        config_file.write_text(yaml.dump(config_content))

        # Mock Path.home() to return our tmp_path
        with patch("pidgin.config.config.Path.home", return_value=tmp_path):
            config = Config()

            # Should have loaded the config
            assert config.get("conversation.convergence_threshold") == 0.95
            assert config.config_path == config_file

    def test_load_from_file_yaml_error(self, tmp_path):
        """Test loading from file with YAML parsing error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        config = Config()

        # Should raise YAML error
        with pytest.raises(yaml.YAMLError):
            config.load_from_file(config_file)

    def test_load_from_file_empty_file(self, tmp_path):
        """Test loading from empty file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = Config()
        original_config = config.config.copy()

        # Should not change config
        config.load_from_file(config_file)
        assert config.config == original_config

    def test_load_from_file_null_content(self, tmp_path):
        """Test loading from file with null content."""
        config_file = tmp_path / "null.yaml"
        config_file.write_text("null")

        config = Config()
        original_config = config.config.copy()

        # Should not change config
        config.load_from_file(config_file)
        assert config.config == original_config

    def test_deep_merge_simple(self):
        """Test simple dictionary merging."""
        config = Config()

        base = {"a": 1, "b": 2}
        update = {"b": 3, "c": 4}

        result = config._deep_merge(base, update)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test nested dictionary merging."""
        config = Config()

        base = {"level1": {"level2": {"a": 1, "b": 2}, "other": "value"}}
        update = {"level1": {"level2": {"b": 3, "c": 4}}}

        result = config._deep_merge(base, update)

        expected = {"level1": {"level2": {"a": 1, "b": 3, "c": 4}, "other": "value"}}

        assert result == expected

    def test_deep_merge_replace_non_dict(self):
        """Test that non-dict values are replaced, not merged."""
        config = Config()

        base = {"key": {"nested": "value"}}
        update = {"key": "string"}

        result = config._deep_merge(base, update)

        assert result == {"key": "string"}

    def test_get_nested_key(self):
        """Test getting nested configuration values."""
        config = Config()

        # Test existing nested key
        assert (
            config.get("conversation.convergence_threshold")
            == DEFAULT_CONVERGENCE_THRESHOLD
        )

        # Test non-existent nested key
        assert config.get("nonexistent.key") is None
        assert config.get("nonexistent.key", "default") == "default"

        # Test partial path exists
        assert config.get("conversation.nonexistent") is None

    def test_get_single_key(self):
        """Test getting single-level configuration values."""
        config = Config()

        # Test existing key
        assert config.get("conversation") is not None

        # Test non-existent key
        assert config.get("nonexistent") is None
        assert config.get("nonexistent", "default") == "default"

    def test_set_new_nested_key(self):
        """Test setting new nested configuration values."""
        config = Config()

        # Set new nested key
        config.set("new.nested.key", "value")

        assert config.get("new.nested.key") == "value"

    def test_set_validation_error(self):
        """Test setting invalid values raises validation error."""
        config = Config()

        # Test invalid convergence threshold
        with pytest.raises(ValueError, match="Invalid value"):
            config.set("conversation.convergence_threshold", -0.5)

        # Test invalid convergence action
        with pytest.raises(ValueError, match="Invalid value"):
            config.set("conversation.convergence_action", "invalid")

    def test_save_with_path(self, tmp_path):
        """Test saving configuration to specific path."""
        config = Config()
        save_path = tmp_path / "saved_config.yaml"

        config.save(save_path)

        assert save_path.exists()

        # Load and verify
        with open(save_path, "r") as f:
            saved_config = yaml.safe_load(f)

        assert (
            saved_config["conversation"]["convergence_threshold"]
            == DEFAULT_CONVERGENCE_THRESHOLD
        )

    def test_save_with_config_path(self, tmp_path):
        """Test saving configuration using stored config_path."""
        config_path = tmp_path / "config.yaml"

        # Create a minimal config file first
        config_path.write_text("conversation:\n  convergence_threshold: 0.8")

        config = Config(config_path=config_path)

        # Save without specifying path
        config.save()

        assert config_path.exists()

    def test_save_without_path(self, tmp_path):
        """Test saving configuration without path (uses cwd)."""
        config = Config()

        with patch("pidgin.config.config.Path.cwd", return_value=tmp_path):
            config.save()

        expected_path = tmp_path / "pidgin.yaml"
        assert expected_path.exists()

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates directory if it doesn't exist."""
        config = Config()
        save_path = tmp_path / "new_dir" / "config.yaml"

        config.save(save_path)

        assert save_path.exists()
        assert save_path.parent.exists()

    def test_get_convergence_config_default_profile(self):
        """Test getting convergence config with default profile."""
        config = Config()

        conv_config = config.get_convergence_config()

        assert conv_config["convergence_threshold"] == DEFAULT_CONVERGENCE_THRESHOLD
        assert conv_config["convergence_action"] == DEFAULT_CONVERGENCE_ACTION
        assert conv_config["profile"] == DEFAULT_CONVERGENCE_PROFILE
        assert "weights" in conv_config
        assert (
            conv_config["weights"]
            == DEFAULT_CONVERGENCE_WEIGHTS[DEFAULT_CONVERGENCE_PROFILE]
        )

    def test_get_convergence_config_custom_profile(self):
        """Test getting convergence config with custom profile."""
        config = Config()

        # Set custom profile
        config.set("convergence.profile", ConvergenceProfiles.CUSTOM)
        custom_weights = {
            ConvergenceComponents.CONTENT: 0.5,
            ConvergenceComponents.STRUCTURE: 0.2,
            ConvergenceComponents.SENTENCES: 0.1,
            ConvergenceComponents.LENGTH: 0.1,
            ConvergenceComponents.PUNCTUATION: 0.1,
        }
        config.set("convergence.custom_weights", custom_weights)

        conv_config = config.get_convergence_config()

        assert conv_config["profile"] == ConvergenceProfiles.CUSTOM
        assert conv_config["weights"] == custom_weights

    def test_get_convergence_config_invalid_profile(self):
        """Test getting convergence config with invalid profile."""
        config = Config()

        # Set invalid profile
        config.config["convergence"] = {"profile": "invalid_profile"}

        conv_config = config.get_convergence_config()

        # Should fall back to default
        assert (
            conv_config["weights"]
            == DEFAULT_CONVERGENCE_WEIGHTS[DEFAULT_CONVERGENCE_PROFILE]
        )

    def test_validate_convergence_weights_valid(self):
        """Test validation of valid convergence weights."""
        config = Config()

        valid_weights = {
            ConvergenceComponents.CONTENT: 0.3,
            ConvergenceComponents.STRUCTURE: 0.2,
            ConvergenceComponents.SENTENCES: 0.2,
            ConvergenceComponents.LENGTH: 0.2,
            ConvergenceComponents.PUNCTUATION: 0.1,
        }

        # Should not raise exception
        config._validate_convergence_weights(valid_weights)

    def test_validate_convergence_weights_missing_components(self):
        """Test validation with missing components."""
        config = Config()

        incomplete_weights = {
            ConvergenceComponents.CONTENT: 0.5,
            ConvergenceComponents.STRUCTURE: 0.5,
        }

        with pytest.raises(ValueError, match="Missing components"):
            config._validate_convergence_weights(incomplete_weights)

    def test_validate_convergence_weights_extra_components(self):
        """Test validation with extra components."""
        config = Config()

        weights_with_extra = {
            ConvergenceComponents.CONTENT: 0.2,
            ConvergenceComponents.STRUCTURE: 0.2,
            ConvergenceComponents.SENTENCES: 0.2,
            ConvergenceComponents.LENGTH: 0.2,
            ConvergenceComponents.PUNCTUATION: 0.2,
            "extra_component": 0.1,
        }

        with pytest.raises(ValueError, match="Unknown components"):
            config._validate_convergence_weights(weights_with_extra)

    def test_validate_convergence_weights_invalid_sum(self):
        """Test validation with weights that don't sum to 1.0."""
        config = Config()

        invalid_weights = {
            ConvergenceComponents.CONTENT: 0.3,
            ConvergenceComponents.STRUCTURE: 0.3,
            ConvergenceComponents.SENTENCES: 0.3,
            ConvergenceComponents.LENGTH: 0.3,
            ConvergenceComponents.PUNCTUATION: 0.3,  # Sum = 1.5
        }

        with pytest.raises(ValueError, match="must sum to 1.0"):
            config._validate_convergence_weights(invalid_weights)

    def test_validate_convergence_weights_floating_point_tolerance(self):
        """Test validation allows small floating point errors."""
        config = Config()

        # Sum = 0.999 (within tolerance)
        weights = {
            ConvergenceComponents.CONTENT: 0.299,
            ConvergenceComponents.STRUCTURE: 0.2,
            ConvergenceComponents.SENTENCES: 0.2,
            ConvergenceComponents.LENGTH: 0.2,
            ConvergenceComponents.PUNCTUATION: 0.1,
        }

        # Should not raise exception
        config._validate_convergence_weights(weights)

    def test_get_context_config(self):
        """Test getting context management configuration."""
        config = Config()

        context_config = config.get_context_config()

        assert context_config["enabled"] is True
        assert context_config["warning_threshold"] == 80
        assert context_config["auto_pause_threshold"] == 95
        assert context_config["show_usage"] is True

    def test_get_provider_config(self):
        """Test getting provider configuration."""
        config = Config()

        provider_config = config.get_provider_config()

        assert "context_management" in provider_config
        assert "rate_limiting" in provider_config
        assert provider_config["context_management"]["enabled"] is True
        assert provider_config["rate_limiting"]["enabled"] is True

    def test_apply_experiment_profile_existing(self):
        """Test applying existing experiment profile."""
        config = Config()

        # Apply unattended profile
        config.apply_experiment_profile("unattended")

        assert config.get("conversation.convergence_threshold") == 0.75
        assert config.get("conversation.convergence_action") == "stop"

    def test_apply_experiment_profile_nonexistent(self):
        """Test applying non-existent experiment profile."""
        config = Config()
        original_threshold = config.get("conversation.convergence_threshold")

        # Apply non-existent profile
        config.apply_experiment_profile("nonexistent")

        # Should not change anything
        assert config.get("conversation.convergence_threshold") == original_threshold

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Config()

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "conversation" in config_dict
        assert "defaults" in config_dict
        assert "context_management" in config_dict

        # Should be a copy, not the original
        assert config_dict is not config.config

    def test_write_example_config(self, tmp_path):
        """Test writing example configuration file."""
        config = Config()
        example_path = tmp_path / "example.yaml"

        config._write_example_config(example_path)

        assert example_path.exists()

        # Load and verify it's valid YAML
        with open(example_path, "r") as f:
            example_content = yaml.safe_load(f)

        assert "conversation" in example_content
        assert "convergence" in example_content
        assert example_content["conversation"]["convergence_threshold"] == 0.85


class TestGlobalConfig:
    """Test global configuration functions."""

    def test_get_config_singleton(self):
        """Test that get_config returns singleton instance."""
        # Clear global state
        import pidgin.config.config as config_module

        config_module._config = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_load_config_updates_global(self, tmp_path):
        """Test that load_config updates global instance."""
        import pidgin.config.config as config_module

        # Create a config file
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            """
conversation:
  convergence_threshold: 0.95
"""
        )

        config = load_config(config_file)

        assert config.get("conversation.convergence_threshold") == 0.95
        assert config_module._config is config
        assert get_config() is config

    def test_check_and_create_config_exists(self, tmp_path):
        """Test _check_and_create_config when config exists."""
        config_dir = tmp_path / ".config" / "pidgin"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "pidgin.yaml"

        config_content = {"conversation": {"convergence_threshold": 0.95}}
        config_file.write_text(yaml.dump(config_content))

        config = Config()

        with patch("pidgin.config.config.Path.home", return_value=tmp_path):
            config._check_and_create_config()

            assert config.get("conversation.convergence_threshold") == 0.95

    def test_check_and_create_config_user_declines(self, tmp_path):
        """Test _check_and_create_config when user declines to create config."""
        config = Config()

        with patch("pidgin.config.config.Path.home", return_value=tmp_path):
            with patch("pidgin.config.config.Console") as mock_console:
                mock_console.return_value.input.return_value = "n"

                config._check_and_create_config()

                # Should not create config file
                config_path = tmp_path / ".config" / "pidgin" / "pidgin.yaml"
                assert not config_path.exists()

    def test_check_and_create_config_user_accepts(self, tmp_path):
        """Test _check_and_create_config when user accepts to create config."""
        config = Config()

        with patch("pidgin.config.config.Path.home", return_value=tmp_path):
            with patch("pidgin.config.config.Console") as mock_console:
                mock_console.return_value.input.return_value = "y"

                config._check_and_create_config()

                # Should create config file
                config_path = tmp_path / ".config" / "pidgin" / "pidgin.yaml"
                assert config_path.exists()

                # Should have loaded the config
                assert config.config_path == config_path
