# cli/ollama_setup.py
"""Ollama setup and model management for CLI."""

import subprocess
from typing import Tuple, Optional, Set
import click
from rich.console import Console
from rich.panel import Panel

from ..local.ollama_helper import ensure_ollama_ready, check_ollama_running, start_ollama_server
from ..config.models import get_model_config

async def normalize_local_model_names(model_a: str, model_b: str, console: Console) -> Tuple[str, str]:
    """Handle 'local' shorthand with interactive selection."""
    if model_a == "local" or model_b == "local":
        # Ensure Ollama is ready (auto-install if needed)
        if not await ensure_ollama_ready(console):
            console.print("\n[#4c566a]Using test model instead[/#4c566a]")
            if model_a == "local": model_a = "local:test"
            if model_b == "local": model_b = "local:test"
            return model_a, model_b
        
        # Show selection menu
        console.print("\n◆ Select local model:")
        console.print("  1. [#88c0d0]qwen[/] - 500MB, fast")
        console.print("  2. [#88c0d0]phi[/] - 2.8GB, balanced")
        console.print("  3. [#88c0d0]mistral[/] - 4.1GB, best, 8GB+ RAM")
        console.print("  4. [#a3be8c]test[/] - no download, pattern-based")
        console.print()
        
        models = ["qwen", "phi", "mistral", "test"]
        
        if model_a == "local":
            choice = click.prompt("First agent", type=int, default=1)
            model_a = f"local:{models[choice-1] if 1 <= choice <= 4 else models[0]}"
            
        if model_b == "local":
            choice = click.prompt("Second agent", type=int, default=1)
            model_b = f"local:{models[choice-1] if 1 <= choice <= 4 else models[0]}"
    
    return model_a, model_b

async def ensure_ollama_models_ready(model_a: str, model_b: str, console: Console) -> bool:
    """Ensure Ollama is running and models are downloaded."""
    # Check if we need Ollama
    using_ollama = False
    models_to_check = set()
    
    for model in [model_a, model_b]:
        if model.startswith("local:") and model != "local:test":
            config = get_model_config(model)
            if config and config.provider == "ollama":
                using_ollama = True
                # Map to actual Ollama model name
                model_name = model.split(":", 1)[1]
                model_map = {
                    "qwen": "qwen2.5:0.5b",
                    "phi": "phi3",
                    "mistral": "mistral"
                }
                ollama_model = model_map.get(model_name, model_name)
                models_to_check.add(ollama_model)
    
    if not using_ollama:
        return True
    
    # Ensure server is running
    if not check_ollama_running():
        started = await start_ollama_server(console)
        if not started:
            console.print("\n[#bf616a]Failed to start Ollama server[/#bf616a]")
            console.print("Please start manually: [#88c0d0]ollama serve[/#88c0d0]")
            return False
    
    # Check and download models
    for ollama_model in models_to_check:
        if not await check_and_pull_model(ollama_model, console):
            return False
    
    return True

async def check_and_pull_model(model_name: str, console: Console) -> bool:
    """Check if model exists, download if needed."""
    # Check if model exists
    result = subprocess.run(
        f"ollama list | grep -q '{model_name}'",
        shell=True,
        capture_output=True
    )
    
    if result.returncode != 0:
        # Model not found, need to download
        console.print()
        console.print(Panel(
            f"[bold #88c0d0]◆ Model Setup: {model_name}[/bold #88c0d0]\n\n"
            f"[#d8dee9]Model not found locally.[/#d8dee9]\n"
            # ... rest of the panel content
        ))
        
        if click.confirm("Download model?", default=True):
            # ... download logic
            pass
    
    return True