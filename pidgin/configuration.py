"""Configuration management for Pidgin."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager for Pidgin."""
    
    DEFAULT_CONFIG = {
        'conversation': {
            'checkpoint': {
                'enabled': True,
                'auto_save_interval': 10
            },
            'basin_detection': {
                'enabled': True,
                'check_interval': 5,
                'detectors': {
                    'structural': {
                        'enabled': True,
                        'window_size': 20,
                        'repetition_threshold': 3
                    },
                    'pattern': {
                        'enabled': True,
                        'gratitude_threshold': 5,
                        'compression_threshold': 20,
                        'emoji_loop_threshold': 5
                    }
                },
                'on_basin_detected': 'stop',
                'log_detection_reasoning': True
            }
        },
        'experiments': {
            'unattended': {
                'basin_detection': {
                    'on_basin_detected': 'stop',
                    'detectors': {
                        'structural': {
                            'repetition_threshold': 2
                        }
                    }
                }
            }
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_path = config_path
        
        # Load from file if provided
        if config_path:
            self.load_from_file(config_path)
        else:
            # Try to load from standard locations
            self._load_from_standard_locations()
    
    def _load_from_standard_locations(self):
        """Load config from standard locations in order of precedence."""
        config_locations = [
            Path.cwd() / 'pidgin.yaml',
            Path.cwd() / '.pidgin.yaml',
            Path.home() / '.config' / 'pidgin' / 'config.yaml',
            Path.home() / '.pidgin.yaml'
        ]
        
        for location in config_locations:
            if location.exists():
                self.load_from_file(location)
                break
    
    def load_from_file(self, path: Path):
        """Load configuration from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r') as f:
            user_config = yaml.safe_load(f)
        
        if user_config:
            self.config = self._deep_merge(self.config, user_config)
            self.config_path = path
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'conversation.checkpoint.enabled')."""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """Set config value using dot notation."""
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    def save(self, path: Optional[Path] = None):
        """Save configuration to file."""
        save_path = path or self.config_path
        if not save_path:
            save_path = Path.cwd() / 'pidgin.yaml'
        
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def get_checkpoint_config(self) -> Dict[str, Any]:
        """Get checkpoint-related configuration."""
        return self.get('conversation.checkpoint', {})
    
    def get_basin_config(self) -> Dict[str, Any]:
        """Get basin detection configuration."""
        return self.get('conversation.basin_detection', {})
    
    def apply_experiment_profile(self, profile: str):
        """Apply an experiment profile to current config."""
        if profile_config := self.get(f'experiments.{profile}'):
            self.config = self._deep_merge(self.config, {'conversation': profile_config})


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def load_config(path: Path) -> Config:
    """Load config from specific path."""
    global _config
    _config = Config(path)
    return _config