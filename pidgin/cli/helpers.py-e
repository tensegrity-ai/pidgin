# pidgin/cli/helpers.py
"""Shared helper functions for CLI commands."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.prompt import Confirm, Prompt

from ..config.dimensional_prompts import DimensionalPromptGenerator
from ..config.models import MODELS, get_model_config
from ..config.prompts import build_initial_prompt
from ..providers.builder import build_provider
from ..ui.display_utils import DisplayUtils
from .constants import MODEL_GLYPHS, NORD_GREEN, NORD_RED, NORD_YELLOW, PROVIDER_COLORS

console = Console()
display = DisplayUtils(console)


async def get_provider_for_model(model_id: str, temperature: Optional[float] = None):
    """Create a provider instance for the given model.

    This is a compatibility wrapper that delegates to the new provider builder.

    Args:
        model_id: Model identifier (e.g., 'gpt-4', 'claude', 'gemini-1.5-pro')
        temperature: Optional temperature override (not used here, temperature is passed to stream_response)

    Returns:
        Provider instance
    """
    return await build_provider(model_id, temperature)


def build_initial_prompt(
    custom_prompt: Optional[str] = None, dimensions: Optional[List[str]] = None
) -> str:
    """Build the initial prompt for a conversation.

    Args:
        custom_prompt: Custom prompt text (overrides dimensions)
        dimensions: List of dimension specifications (e.g., ["peers:philosophy:analytical"])

    Returns:
        The initial prompt string
    """
    if custom_prompt:
        return custom_prompt

    if not dimensions:
        return "I'm looking forward to your conversation."

    # Use the DimensionalPromptGenerator
    generator = DimensionalPromptGenerator()

    # If multiple dimensions provided, use the first one
    # (The original CLI only uses one dimension spec at a time)
    if dimensions:
        try:
            dimension_spec = dimensions[0]  # Take the first dimension spec
            return generator.generate(dimension_spec)
        except ValueError as e:
            display.warning(str(e), use_panel=False)
            return "I'm looking forward to your conversation."

    return "I'm looking forward to your conversation."


def validate_model_id(model_id: str) -> Tuple[str, str]:
    """Validate and normalize a model identifier.

    Args:
        model_id: Model ID from user input

    Returns:
        Tuple of (validated_id, display_name)

    Raises:
        ValueError: If model ID is invalid
    """
    # Handle silent model
    if model_id == "silent":
        return "silent", "Silent"

    # Check if it's a known model
    config = get_model_config(model_id)
    if config:
        return model_id, config.shortname

    # Try provider:model format
    if ":" in model_id:
        provider, model_name = model_id.split(":", 1)
        if provider == "local":
            # For local models, check if Ollama is available
            if not check_ollama_available():
                raise ValueError("Ollama is not running. Start it with 'ollama serve'")
            return model_id, f"Local: {model_name}"

    raise ValueError(f"Unknown model: {model_id}")


def check_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    import httpx

    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
        return False


def format_model_display(model_id: str) -> str:
    """Format model ID for display with emoji and color."""
    config = get_model_config(model_id)
    if not config:
        return model_id

    glyph = MODEL_GLYPHS.get(model_id, "●")
    color = PROVIDER_COLORS.get(config.provider, "white")

    return f"{glyph} [{color}]{config.shortname}[/{color}]"


def find_conversations(path: Optional[str] = None, pattern: str = "*") -> List[Path]:
    """Find conversation directories.

    Args:
        path: Base path to search (defaults to ./pidgin_output)
        pattern: Glob pattern for filtering

    Returns:
        List of conversation directory paths
    """
    if path:
        base_path = Path(path)
    else:
        base_path = Path("./pidgin_output/conversations")

    if not base_path.exists():
        return []

    # Find all conversation directories
    conversations = []

    # Search in date directories
    for date_dir in base_path.glob("*"):
        if date_dir.is_dir() and not date_dir.name.startswith("."):
            for conv_dir in date_dir.glob(pattern):
                if conv_dir.is_dir() and (conv_dir / "transcript.md").exists():
                    conversations.append(conv_dir)

    return sorted(conversations, key=lambda p: p.stat().st_mtime, reverse=True)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def load_conversation_metadata(conv_dir: Path) -> Dict[str, Any]:
    """Load metadata from a conversation directory."""
    metadata = {}

    # Try to load state.json
    state_file = conv_dir / "state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
                metadata["agents"] = state.get("agents", [])
                metadata["total_turns"] = state.get("total_turns", 0)
                metadata["started_at"] = state.get("started_at", "")
        except (json.JSONDecodeError, OSError, KeyError):
            # State file might be corrupted or inaccessible
            pass

    # Get file sizes
    transcript = conv_dir / "transcript.md"
    if transcript.exists():
        metadata["transcript_size"] = transcript.stat().st_size

    events = conv_dir / "events.jsonl"
    if events.exists():
        metadata["events_size"] = events.stat().st_size

    return metadata


async def confirm_action(message: str, default: bool = False) -> bool:
    """Async wrapper for rich.prompt.Confirm."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: Confirm.ask(message, default=default)
    )


async def prompt_for_input(message: str, default: Optional[str] = None) -> str:
    """Async wrapper for rich.prompt.Prompt."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: (
            Prompt.ask(message, default=default) if default else Prompt.ask(message)
        ),
    )


def parse_temperature(value: str) -> float:
    """Parse and validate temperature value."""
    try:
        temp = float(value)
        if not 0.0 <= temp <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return temp
    except ValueError as e:
        raise click.BadParameter(str(e))


def parse_dimensions(dimensions: List[str]) -> List[str]:
    """Parse and validate dimension specifications.

    Args:
        dimensions: List of dimension specs like ["peers:philosophy:analytical"]

    Returns:
        List of valid dimension specifications
    """
    generator = DimensionalPromptGenerator()
    valid_dims = []

    for dim_spec in dimensions:
        try:
            # Try to generate a prompt to validate the dimension spec
            generator.generate(dim_spec)
            valid_dims.append(dim_spec)
        except ValueError as e:
            display.warning(
                f"Invalid dimension spec '{dim_spec}': {e}", use_panel=False
            )

    return valid_dims


def get_experiment_dir(base_dir: Optional[Path] = None) -> Path:
    """Get the experiments directory, ensuring it exists."""
    if base_dir is None:
        base_dir = Path("./pidgin_output")

    exp_dir = base_dir / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)
    return exp_dir
