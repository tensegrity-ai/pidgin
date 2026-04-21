# cli/ollama_setup.py
"""Ollama setup and model management for CLI."""

import subprocess
from typing import Tuple

import click
from rich.console import Console

from ..config.models import get_model_config
from ..providers.ollama_helper import (
    check_ollama_running,
    ensure_ollama_ready,
    start_ollama_server,
)
from ..ui.display_utils import DisplayUtils


async def normalize_local_model_names(
    model_a: str, model_b: str, console: Console
) -> Tuple[str, str]:
    """Handle 'local' shorthand with interactive selection."""
    display = DisplayUtils(console)
    if model_a == "local" or model_b == "local":
        # Ensure Ollama is ready (auto-install if needed)
        if not await ensure_ollama_ready(console):
            console.print()  # Add newline
            display.dim("Using test model instead")
            if model_a == "local":
                model_a = "local:test"
            if model_b == "local":
                model_b = "local:test"
            return model_a, model_b

        # Show selection menu
        menu_lines = [
            "◆ Select local model:",
            "  1. qwen - 522MB, fast (Qwen 3 0.6B)",
            "  2. phi - 2.8GB, balanced",
            "  3. mistral - 4.1GB, best, 8GB+ RAM",
            "  4. test - no download, pattern-based",
        ]
        display.info("\n".join(menu_lines), use_panel=False)
        console.print()

        models = ["qwen", "phi", "mistral", "test"]

        if model_a == "local":
            choice = click.prompt("First agent", type=int, default=1)
            model_a = f"local:{models[choice - 1] if 1 <= choice <= 4 else models[0]}"

        if model_b == "local":
            choice = click.prompt("Second agent", type=int, default=1)
            model_b = f"local:{models[choice - 1] if 1 <= choice <= 4 else models[0]}"

    return model_a, model_b


async def ensure_ollama_models_ready(
    model_a: str, model_b: str, console: Console
) -> bool:
    """Ensure Ollama is running and models are downloaded."""
    display = DisplayUtils(console)
    # Check if we need Ollama
    using_ollama = False
    models_to_check: set[str] = set()

    for model in [model_a, model_b]:
        if model.startswith("local:") and model != "local:test":
            config = get_model_config(model)
            if config and config.provider == "ollama" and config.api.ollama_model:
                using_ollama = True
                models_to_check.add(config.api.ollama_model)

    if not using_ollama:
        return True

    # Ensure server is running
    if not check_ollama_running():
        started = await start_ollama_server(console, prompt_if_needed=True)
        if not started:
            console.print()  # Add newline
            display.error(
                "Failed to start Ollama server",
                context="Please start manually: ollama serve",
                use_panel=False,
            )
            return False

    # Check and download models
    for ollama_model in models_to_check:
        if not await check_and_pull_model(ollama_model, console):
            return False

    return True


async def check_and_pull_model(model_name: str, console: Console) -> bool:
    """Check if model exists, download if needed."""
    display = DisplayUtils(console)
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, check=False
        )
        model_exists = model_name in result.stdout
    except (subprocess.CalledProcessError, OSError):
        model_exists = False

    if model_exists:
        return True

    console.print()
    display.info(
        f"Model Setup: {model_name}\n\n"
        f"Model not found locally.\n"
        f"This model needs to be downloaded first.",
        title="◆ Model Setup",
        use_panel=True,
    )

    if not click.confirm("Download model?", default=True):
        display.dim("Download skipped")
        return False

    display.dim(f"Pulling {model_name} (this may take a while)...")
    try:
        pull_result = subprocess.run(["ollama", "pull", model_name], check=False)
    except (subprocess.CalledProcessError, OSError) as e:
        display.error(f"Failed to run ollama pull: {e}", use_panel=False)
        return False

    if pull_result.returncode != 0:
        display.error(
            f"Failed to pull {model_name}",
            context=f"Try manually: ollama pull {model_name}",
            use_panel=False,
        )
        return False

    display.success(f"Downloaded {model_name}")
    return True
