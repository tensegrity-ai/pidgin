"""Configuration and settings management."""
import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from rich.console import Console

console = Console()


class APIConfig(BaseModel):
    """API configuration for LLM providers."""
    anthropic: Optional[str] = Field(default=None, description="Anthropic API key")
    openai: Optional[str] = Field(default=None, description="OpenAI API key")
    google: Optional[str] = Field(default=None, description="Google API key")


class DefaultConfig(BaseModel):
    """Default experiment configuration."""
    model: str = Field(default="claude-3-opus-20240229", description="Default model")
    max_turns: int = Field(default=100, description="Default maximum turns")
    mediation_level: str = Field(default="observe", description="Default mediation level")
    archetype: str = Field(default="analytical", description="Default archetype")


class UIConfig(BaseModel):
    """UI display configuration."""
    theme: str = Field(default="default", description="Display theme")
    show_timestamps: bool = Field(default=True, description="Show timestamps")
    syntax_highlighting: bool = Field(default=True, description="Enable syntax highlighting")
    live_refresh_rate: float = Field(default=0.5, description="Live view refresh rate")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Configuration paths
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".pidgin",
        description="Configuration directory"
    )
    data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".pidgin" / "data",
        description="Data storage directory"
    )
    
    # Sub-configurations
    api: APIConfig = Field(default_factory=APIConfig)
    defaults: DefaultConfig = Field(default_factory=DefaultConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    
    class Config:
        env_prefix = "PIDGIN_"
        env_nested_delimiter = "__"
    
    def __init__(self, config_path: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        if config_path:
            self.load_config(config_path)
        else:
            self.load_config(self.config_dir / "config.yaml")
        
        # Override with environment variables
        self._load_env_vars()
    
    def _load_env_vars(self):
        """Load API keys from environment variables."""
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            self.api.anthropic = api_key
        if api_key := os.getenv("OPENAI_API_KEY"):
            self.api.openai = api_key
        if api_key := os.getenv("GOOGLE_API_KEY"):
            self.api.google = api_key
    
    def config_exists(self) -> bool:
        """Check if configuration file exists."""
        config_path = self.config_dir / "config.yaml"
        return config_path.exists()
    
    def load_config(self, path: Path):
        """Load configuration from YAML file."""
        if not path.exists():
            return
        
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            
            # Update configurations
            if "api_keys" in data:
                self.api = APIConfig(**data["api_keys"])
            if "defaults" in data:
                self.defaults = DefaultConfig(**data["defaults"])
            if "ui" in data:
                self.ui = UIConfig(**data["ui"])
                
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config: {e}[/yellow]")
    
    def save_config(self, data: Optional[Dict[str, Any]] = None):
        """Save configuration to YAML file."""
        config_path = self.config_dir / "config.yaml"
        
        if data is None:
            data = {
                "api_keys": self.api.dict(exclude_none=True),
                "defaults": self.defaults.dict(),
                "ui": self.ui.dict(),
            }
        
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider."""
        return getattr(self.api, provider.lower(), None)
    
    def has_api_key(self, provider: str) -> bool:
        """Check if API key exists for provider."""
        return bool(self.get_api_key(provider))
    
    @property
    def experiments_dir(self) -> Path:
        """Get experiments directory."""
        path = self.data_dir / "experiments"
        path.mkdir(exist_ok=True)
        return path
    
    @property
    def transcripts_dir(self) -> Path:
        """Get transcripts directory."""
        path = self.data_dir / "transcripts"
        path.mkdir(exist_ok=True)
        return path
    
    @property
    def analysis_dir(self) -> Path:
        """Get analysis directory."""
        path = self.data_dir / "analysis"
        path.mkdir(exist_ok=True)
        return path