# pidgin/tests/cli/test_spec_loader.py
"""Tests for YAML spec file loading and validation."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import yaml

from pidgin.cli.spec_loader import SpecLoader
from pidgin.experiments import ExperimentConfig


class TestSpecLoader:
    """Test suite for SpecLoader class."""
    
    @pytest.fixture
    def spec_loader(self):
        """Create a SpecLoader instance for testing."""
        return SpecLoader()
    
    @pytest.fixture
    def valid_spec(self):
        """Return a valid specification dictionary."""
        return {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "name": "test-experiment",
            "repetitions": 5,
            "max_turns": 10,
            "temperature": 0.7,
            "custom_prompt": "Let's discuss philosophy",
            "dimensions": ["philosophy", "creativity"],
            "convergence_threshold": 0.8,
            "convergence_action": "stop",
            "awareness": "research",
            "choose_names": True,
            "max_parallel": 2,
            "first_speaker": "agent_b",
            "display_mode": "quiet",
            "prompt_tag": "[USER]",
            "allow_truncation": True
        }
    
    @pytest.fixture
    def minimal_spec(self):
        """Return a minimal valid specification."""
        return {
            "agent_a": "claude",
            "agent_b": "gpt-4"
        }
    
    # Tests for load_spec method
    
    def test_load_spec_valid_yaml(self, spec_loader, valid_spec):
        """Test loading a valid YAML spec file."""
        yaml_content = yaml.dump(valid_spec)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = spec_loader.load_spec(Path("test.yaml"))
        
        assert result == valid_spec
    
    def test_load_spec_file_not_found(self, spec_loader):
        """Test loading a non-existent spec file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch.object(spec_loader.display, "error") as mock_error:
                with pytest.raises(FileNotFoundError):
                    spec_loader.load_spec(Path("nonexistent.yaml"))
                
                mock_error.assert_called_once_with("Spec file not found: nonexistent.yaml")
    
    def test_load_spec_invalid_yaml(self, spec_loader):
        """Test loading an invalid YAML file."""
        invalid_yaml = "{ invalid: yaml: content }"
        
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch.object(spec_loader.display, "error") as mock_error:
                with pytest.raises(yaml.YAMLError):
                    spec_loader.load_spec(Path("invalid.yaml"))
                
                # Check that error was displayed
                assert mock_error.called
                error_msg = mock_error.call_args[0][0]
                assert "Invalid YAML" in error_msg
                assert "invalid.yaml" in error_msg
    
    def test_load_spec_generic_error(self, spec_loader):
        """Test handling of generic errors during loading."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch.object(spec_loader.display, "error") as mock_error:
                with pytest.raises(PermissionError):
                    spec_loader.load_spec(Path("test.yaml"))
                
                mock_error.assert_called_once()
                assert "Error loading spec" in mock_error.call_args[0][0]
    
    # Tests for validate_spec method
    
    def test_validate_spec_valid(self, spec_loader, valid_spec):
        """Test validating a valid spec."""
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            # Should not raise any exception
            spec_loader.validate_spec(valid_spec)
            
            # Check models were validated
            assert mock_validate.call_count == 2
            mock_validate.assert_any_call("claude")
            mock_validate.assert_any_call("gpt-4")
    
    def test_validate_spec_with_shorthand(self, spec_loader, minimal_spec):
        """Test validating spec with shorthand model names."""
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            spec_loader.validate_spec(minimal_spec)
            
            # Check that shorthand was converted
            assert minimal_spec["agent_a_model"] == "claude"
            assert minimal_spec["agent_b_model"] == "gpt-4"
            assert "agent_a" not in minimal_spec
            assert "agent_b" not in minimal_spec
    
    def test_validate_spec_missing_models(self, spec_loader):
        """Test validating spec with missing model fields."""
        invalid_spec = {"name": "test", "repetitions": 5}
        
        with pytest.raises(ValueError) as exc_info:
            spec_loader.validate_spec(invalid_spec)
        
        assert "Missing required fields" in str(exc_info.value)
        assert "agent_a_model and agent_b_model" in str(exc_info.value)
    
    def test_validate_spec_invalid_model(self, spec_loader, valid_spec):
        """Test validating spec with invalid model ID."""
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = ValueError("Unknown model: invalid-model")
            
            with pytest.raises(ValueError) as exc_info:
                spec_loader.validate_spec(valid_spec)
            
            assert "Invalid model" in str(exc_info.value)
            assert "Unknown model: invalid-model" in str(exc_info.value)
    
    # Tests for spec_to_config method
    
    def test_spec_to_config_full_spec(self, spec_loader, valid_spec):
        """Test converting a full spec to ExperimentConfig."""
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            config = spec_loader.spec_to_config(valid_spec)
            
            assert isinstance(config, ExperimentConfig)
            assert config.name == "test-experiment"
            assert config.agent_a_model == "claude-3-opus"
            assert config.agent_b_model == "gpt-4"
            assert config.repetitions == 5
            assert config.max_turns == 10
            assert config.temperature_a == 0.7
            assert config.temperature_b == 0.7
            assert config.custom_prompt == "Let's discuss philosophy"
            assert config.dimensions == ["philosophy", "creativity"]
            assert config.convergence_threshold == 0.8
            assert config.convergence_action == "stop"
            assert config.awareness == "research"
            assert config.awareness_a is None
            assert config.awareness_b is None
            assert config.choose_names is True
            assert config.max_parallel == 2
            assert config.first_speaker == "agent_b"
            assert config.display_mode == "quiet"
            assert config.prompt_tag == "[USER]"
            assert config.allow_truncation is True
    
    def test_spec_to_config_minimal_spec(self, spec_loader):
        """Test converting a minimal spec with defaults."""
        minimal_spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4"
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            with patch("pidgin.cli.spec_loader.generate_experiment_name") as mock_name_gen:
                mock_name_gen.return_value = "generated-name"
                
                config = spec_loader.spec_to_config(minimal_spec)
            
            # Check defaults
            assert config.name == "generated-name"
            assert config.repetitions == 1
            assert config.max_turns == 20  # DEFAULT_TURNS
            assert config.temperature_a is None
            assert config.temperature_b is None
            assert config.custom_prompt is None  # "Hello" becomes None
            assert config.dimensions is None
            assert config.convergence_threshold is None
            assert config.convergence_action is None
            assert config.awareness == "basic"
            assert config.choose_names is False
            assert config.max_parallel == 1
            assert config.first_speaker == "agent_a"
            assert config.display_mode == "chat"
            assert config.prompt_tag == "[HUMAN]"
            assert config.allow_truncation is False
    
    def test_spec_to_config_temperature_handling(self, spec_loader):
        """Test different temperature configurations."""
        # Test global temperature
        spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "temperature": 0.5
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ] * 3
            
            config = spec_loader.spec_to_config(spec)
            assert config.temperature_a == 0.5
            assert config.temperature_b == 0.5
            
            # Test individual temperatures override global
            spec["temperature_a"] = 0.3
            spec["temperature_b"] = 0.8
            
            config = spec_loader.spec_to_config(spec)
            assert config.temperature_a == 0.3
            assert config.temperature_b == 0.8
            
            # Test individual without global
            del spec["temperature"]
            config = spec_loader.spec_to_config(spec)
            assert config.temperature_a == 0.3
            assert config.temperature_b == 0.8
    
    def test_spec_to_config_turns_handling(self, spec_loader):
        """Test handling of turns vs max_turns."""
        spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "turns": 30
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ] * 2
            
            config = spec_loader.spec_to_config(spec)
            assert config.max_turns == 30
            
            # max_turns takes precedence
            spec["max_turns"] = 50
            config = spec_loader.spec_to_config(spec)
            assert config.max_turns == 50
    
    def test_spec_to_config_prompt_handling(self, spec_loader):
        """Test handling of prompt vs custom_prompt."""
        spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "prompt": "Discuss AI"
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ] * 3
            
            config = spec_loader.spec_to_config(spec)
            assert config.custom_prompt == "Discuss AI"
            
            # custom_prompt takes precedence
            spec["custom_prompt"] = "Let's talk about philosophy"
            config = spec_loader.spec_to_config(spec)
            assert config.custom_prompt == "Let's talk about philosophy"
            
            # "Hello" becomes None
            spec["custom_prompt"] = "Hello"
            config = spec_loader.spec_to_config(spec)
            assert config.custom_prompt is None
    
    def test_spec_to_config_dimensions_handling(self, spec_loader):
        """Test handling of dimensions vs dimension."""
        spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "dimension": ["philosophy"]
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ] * 3
            
            config = spec_loader.spec_to_config(spec)
            assert config.dimensions == ["philosophy"]
            
            # dimensions takes precedence
            spec["dimensions"] = ["science", "art"]
            config = spec_loader.spec_to_config(spec)
            assert config.dimensions == ["science", "art"]
            
            # Handle string dimension
            spec["dimensions"] = "single-dimension"
            config = spec_loader.spec_to_config(spec)
            assert config.dimensions == ["single-dimension"]
    
    def test_spec_to_config_convergence_defaults(self, spec_loader):
        """Test convergence action defaults."""
        spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "convergence_threshold": 0.9
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            config = spec_loader.spec_to_config(spec)
            assert config.convergence_threshold == 0.9
            assert config.convergence_action == "stop"  # Default when threshold is set
    
    def test_spec_to_config_awareness_settings(self, spec_loader):
        """Test awareness settings handling."""
        spec = {
            "agent_a_model": "claude",
            "agent_b_model": "gpt-4",
            "awareness": "firm",
            "awareness_a": "research",
            "awareness_b": "none"
        }
        
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            config = spec_loader.spec_to_config(spec)
            assert config.awareness == "firm"
            assert config.awareness_a == "research"
            assert config.awareness_b == "none"
    
    # Tests for show_spec_info method
    
    def test_show_spec_info(self, spec_loader):
        """Test displaying spec information."""
        config = ExperimentConfig(
            name="test-experiment",
            agent_a_model="claude-3-opus",
            agent_b_model="gpt-4",
            repetitions=10,
            max_turns=20
        )
        
        with patch("pidgin.cli.spec_loader.get_model_config") as mock_get_config:
            # Mock model configs
            mock_get_config.side_effect = [
                Mock(display_name="Claude 3 Opus"),
                Mock(display_name="GPT-4")
            ]
            
            with patch.object(spec_loader.display, "info") as mock_info:
                spec_loader.show_spec_info(Path("test.yaml"), config)
                
                mock_info.assert_called_once()
                args = mock_info.call_args
                
                # Check main message
                assert "Loading experiment from: test.yaml" in args[0][0]
                
                # Check context
                context = args[1]["context"]
                assert "Name: test-experiment" in context
                assert "Agents: Claude 3 Opus ↔ GPT-4" in context
                assert "Repetitions: 10" in context
    
    def test_show_spec_info_missing_model_config(self, spec_loader):
        """Test displaying spec info when model config is missing."""
        config = ExperimentConfig(
            name="test-experiment",
            agent_a_model="unknown-model-a",
            agent_b_model="unknown-model-b",
            repetitions=5,
            max_turns=15
        )
        
        with patch("pidgin.cli.spec_loader.get_model_config") as mock_get_config:
            # Return None for unknown models
            mock_get_config.side_effect = [None, None]
            
            with patch.object(spec_loader.display, "info") as mock_info:
                spec_loader.show_spec_info(Path("test.yaml"), config)
                
                # Should fall back to model IDs
                context = mock_info.call_args[1]["context"]
                assert "Agents: unknown-model-a ↔ unknown-model-b" in context
    
    # Integration tests
    
    def test_full_spec_loading_flow(self, spec_loader, valid_spec):
        """Test the complete flow: load -> validate -> convert -> display."""
        yaml_content = yaml.dump(valid_spec)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
                mock_validate.side_effect = [
                    ("claude-3-opus", "Claude 3 Opus"),
                    ("gpt-4", "GPT-4")
                ] * 2
                
                with patch("pidgin.cli.spec_loader.get_model_config") as mock_get_config:
                    mock_get_config.side_effect = [
                        Mock(display_name="Claude 3 Opus"),
                        Mock(display_name="GPT-4")
                    ]
                    
                    # Load spec
                    spec = spec_loader.load_spec(Path("test.yaml"))
                    
                    # Validate spec
                    spec_loader.validate_spec(spec)
                    
                    # Convert to config
                    config = spec_loader.spec_to_config(spec)
                    
                    # Show info
                    with patch.object(spec_loader.display, "info"):
                        spec_loader.show_spec_info(Path("test.yaml"), config)
                    
                    # Verify final config
                    assert config.name == "test-experiment"
                    assert config.agent_a_model == "claude-3-opus"
                    assert config.agent_b_model == "gpt-4"
    
    def test_spec_with_invalid_then_valid(self, spec_loader):
        """Test error recovery: invalid spec followed by valid spec."""
        invalid_spec = {"name": "test"}  # Missing required fields
        valid_spec = {
            "agent_a": "claude",
            "agent_b": "gpt-4"
        }
        
        # First attempt should fail
        with pytest.raises(ValueError):
            spec_loader.validate_spec(invalid_spec.copy())
        
        # Second attempt should succeed
        with patch("pidgin.cli.spec_loader.validate_model_id") as mock_validate:
            mock_validate.side_effect = [
                ("claude-3-opus", "Claude 3 Opus"),
                ("gpt-4", "GPT-4")
            ]
            
            spec_loader.validate_spec(valid_spec.copy())
            # Should succeed without raising