"""Configuration management for Pidgin."""

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
            'attractor_detection': {
                'enabled': True,
                'check_interval': 5,
                'window_size': 10,
                'threshold': 3,
                'on_detection': 'stop'
            }
        },
        'context_management': {
            'enabled': True,
            'warning_threshold': 80,  # Warn at 80% capacity
            'auto_pause_threshold': 95,  # Auto-pause at 95% capacity
            'show_usage': True  # Display context usage in UI
        },
        'defaults': {
            'max_turns': 20,
            'manual_mode': False,
            'convergence_threshold': 0.75,
            'streaming_interrupts': False  # Removed - using Ctrl+Z signals instead
        },
        'experiments': {
            'unattended': {
                'attractor_detection': {
                    'on_detection': 'stop',
                    'threshold': 2,  # More aggressive
                    'window_size': 8
                }
            },
            'baseline': {
                'attractor_detection': {
                    'enabled': False
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
            Path.home() / '.config' / 'pidgin' / 'pidgin.yaml',  # XDG standard
            Path.home() / '.config' / 'pidgin.yaml',             # XDG config location
            Path.home() / '.pidgin.yaml',                        # Home directory
            Path.cwd() / 'pidgin.yaml',                          # Current directory
            Path.cwd() / '.pidgin.yaml',                         # Hidden in current dir
        ]
        
        for location in config_locations:
            if location.exists():
                print(f"Loading config from: {location}")
                self.load_from_file(location)
                break
        else:
            print("No config file found, using defaults")
    
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
    
    def get_attractor_config(self) -> Dict[str, Any]:
        """Get attractor detection configuration."""
        return self.get('conversation.attractor_detection', {})
    
    def get_context_config(self) -> Dict[str, Any]:
        """Get context management configuration."""
        return self.get('context_management', {})
    
    def apply_experiment_profile(self, profile: str):
        """Apply an experiment profile to current config."""
        if profile_config := self.get(f'experiments.{profile}'):
            self.config = self._deep_merge(self.config, {'conversation': profile_config})
    
    def to_dict(self) -> Dict[str, Any]:
        """Return the full configuration as a dictionary."""
        return self.config.copy()


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