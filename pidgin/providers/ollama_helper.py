"""Ollama installation and management helper."""

import asyncio
import os
import platform
import socket
import subprocess

import click

from ..config.config import Config
from ..ui.display_utils import DisplayUtils


def should_auto_start_ollama() -> bool:
    """Check if Ollama should auto-start based on config or environment."""
    # Check environment variable first
    if os.environ.get("PIDGIN_OLLAMA_AUTO_START", "").lower() in ["true", "1", "yes"]:
        return True

    # Check config file
    try:
        config = Config()
        return config.get("ollama.auto_start", False)
    except Exception:
        # If config loading fails, default to False
        return False


def check_ollama_installed() -> bool:
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_ollama_running() -> bool:
    """Check if Ollama server is running."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", 11434))
        sock.close()
        return result == 0
    except OSError:
        # Socket creation or connection failed
        return False


def get_install_instructions() -> str:
    """Get platform-specific install instructions."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return "Download from https://ollama.ai/download or use: brew install ollama"
    elif system == "Linux":
        return "curl -fsSL https://ollama.ai/install.sh | sh"
    elif system == "Windows":
        return "Download from https://ollama.ai/download/windows"
    else:
        return "Visit https://ollama.ai"


async def start_ollama_server(console, prompt_if_needed: bool = True) -> bool:
    """Start Ollama server automatically in background."""
    if check_ollama_running():
        return True

    # Check if we should auto-start
    if not should_auto_start_ollama() and prompt_if_needed:
        display = DisplayUtils(console)
        display.info("Ollama server is not running", use_panel=False)
        if not click.confirm("Start Ollama server?", default=True):
            return False

    try:
        # Start in background silently
        if platform.system() == "Windows":
            # CREATE_NEW_CONSOLE is Windows-specific
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
            subprocess.Popen(["ollama", "serve"], creationflags=creation_flags)
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Wait for it to start (up to 5 seconds)
        for i in range(10):
            await asyncio.sleep(0.5)
            if check_ollama_running():
                # Only show a subtle notice that it started
                display = DisplayUtils(console)
                display.dim("◆ Ollama server started (stop with: ollama stop)")
                return True

        return False

    except Exception:
        return False


async def auto_install_ollama(console) -> bool:
    """Auto-install Ollama with user permission already granted."""
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # Check if Homebrew is installed
            brew_check = subprocess.run(["which", "brew"], capture_output=True)
            if brew_check.returncode != 0:
                display = DisplayUtils(console)
                display.warning("Homebrew not found", use_panel=False)
                display.info("Install Homebrew first: https://brew.sh", use_panel=False)
                display.info("Then run: brew install ollama", use_panel=False)
                return False

            display = DisplayUtils(console)
            display.dim("Installing Ollama via Homebrew...")
            display.dim("This may take a few minutes\n")

            # Install with Homebrew (quietly)
            result = subprocess.run(
                ["brew", "install", "--quiet", "ollama"],
                capture_output=True,  # Capture output to keep it clean
                text=True,
            )

            if result.returncode == 0:
                console.print()  # Add spacing
                display.success("Ollama installed successfully!")
                return True
            else:
                console.print()  # Add spacing
                display.error("Installation failed", use_panel=False)
                display.dim("Try running manually: brew install ollama")
                return False

        elif system == "Linux":
            display.warning(
                "WARNING: This will download and execute a remote script",
                use_panel=False,
            )
            display.dim("   Script URL: https://ollama.ai/install.sh")
            display.dim("   This installs Ollama to /usr/local/bin/ollama")
            console.print()

            if not click.confirm(
                "Continue with remote script execution?", default=False
            ):
                display.dim("Installation cancelled. Manual install:")
                display.info(
                    "  curl -fsSL https://ollama.ai/install.sh | sh", use_panel=False
                )
                return False

            display.dim("Downloading and installing Ollama...")

            # Download and run the install script in two steps for security
            # First download the script
            download_result = subprocess.run(
                ["curl", "-fsSL", "https://ollama.ai/install.sh"],
                capture_output=True,
                text=True,
            )

            if download_result.returncode != 0:
                display.error("Failed to download Ollama installer")
                return False

            # Then run it through sh
            result = subprocess.run(
                ["sh"],
                input=download_result.stdout,
                text=True,
                capture_output=False,
            )

            if result.returncode == 0:
                console.print()  # Add spacing
                display.success("Ollama installed successfully!")
                return True
            else:
                display = DisplayUtils(console)
                display.error("Installation failed", use_panel=False)
                return False

        elif system == "Windows":
            display.warning("Windows requires manual installation", use_panel=False)
            display.info(
                "Download from: https://ollama.ai/download/windows", use_panel=False
            )
            return False
        else:
            # Unsupported system
            display = DisplayUtils(console)
            display.warning(f"Unsupported system: {system}", use_panel=False)
            return False

    except KeyboardInterrupt:
        console.print()  # Add spacing
        display.warning("Installation cancelled", use_panel=False)
        return False
    except Exception as e:
        display.error(f"Install error: {e!s}", use_panel=False)
        return False


async def ensure_ollama_ready(console) -> bool:
    """Ensure Ollama is installed and running with graceful auto-install."""
    display = DisplayUtils(console)

    # Step 1: Check if installed
    if not check_ollama_installed():
        display = DisplayUtils(console)
        info_lines = [
            "◆ Ollama is required for local models",
            "  Download size: ~150MB",
            "  Installs to: /usr/local/bin/ollama",
        ]
        display.info("\n".join(info_lines), use_panel=False)
        console.print()

        if click.confirm("Install Ollama now?", default=True):
            # Auto-install with progress
            success = await auto_install_ollama(console)
            if not success:
                console.print()  # Add spacing
                display.warning("Manual install required:", use_panel=False)
                display.info(f"  {get_install_instructions()}", use_panel=False)
                return False
        else:
            console.print()  # Add spacing
            display.dim("Using test model instead")
            return False

    # Step 2: Check if running, start if needed
    if not check_ollama_running():
        # Start the server (will check auto-start config)
        success = await start_ollama_server(console, prompt_if_needed=True)
        if not success:
            display = DisplayUtils(console)
            console.print()  # Add spacing
            display.warning("Failed to start Ollama server", use_panel=False)
            display.info("Please start manually: ollama serve", use_panel=False)
            return False

    return True
