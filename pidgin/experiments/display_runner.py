"""Display runner that tails JSONL files and shows live updates."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Union

from rich.console import Console

from ..core.event_bus import EventBus
from ..core.types import Agent
from ..io.event_deserializer import EventDeserializer
from ..io.paths import get_experiments_dir
from ..ui.chat_display import ChatDisplay
from ..ui.tail import TailDisplay

console = Console()


async def run_display(experiment_id: str, display_mode: str = "tail"):
    """Run live display by tailing JSONL files.

    Args:
        experiment_id: The experiment ID to display
        display_mode: Display mode ('tail', 'chat', or 'none')
    """
    if display_mode == "none":
        return

    # Set process title for display runner
    try:
        import setproctitle

        if display_mode == "chat":
            setproctitle.setproctitle("pidgin-chat")
        else:
            setproctitle.setproctitle("pidgin-tail")
    except ImportError:
        pass  # Optional dependency

    exp_dir = get_experiments_dir() / experiment_id
    if not exp_dir.exists():
        console.print(f"[red]Experiment directory not found: {exp_dir}[/red]")
        return

    # Create event bus and display
    bus = EventBus()

    _display: Union[ChatDisplay, TailDisplay]
    if display_mode == "chat":
        # For chat display, we need to create dummy agents
        # In the future, we could read this from manifest
        agents = {
            "agent_a": Agent(id="agent_a", model="unknown", display_name="Agent A"),
            "agent_b": Agent(id="agent_b", model="unknown", display_name="Agent B"),
        }
        _display = ChatDisplay(bus, console, agents)
    else:
        # Default to tail display
        _display = TailDisplay(bus, console)

    # Track file positions
    file_positions: Dict[Path, int] = {}

    # Get initial JSONL files
    jsonl_files: List[Path] = list(exp_dir.glob("*.jsonl"))

    # Also check for experiment-level events file
    experiment_events_file = exp_dir / f"{experiment_id}_events.jsonl"
    if experiment_events_file.exists() and experiment_events_file not in jsonl_files:
        jsonl_files.append(experiment_events_file)

    # Track if we need to check for new files
    check_for_new_files = False

    # Read manifest to check if experiment is still running
    manifest_path = exp_dir / "manifest.json"

    try:
        while True:
            events_found = False

            # Check for new JSONL files if needed (after conversation ends)
            if check_for_new_files:
                new_files = list(exp_dir.glob("*.jsonl"))
                for f in new_files:
                    if f not in file_positions:
                        jsonl_files.append(f)
                        file_positions[f] = 0
                check_for_new_files = False

            # Initialize positions for any files we haven't seen
            for jsonl_file in jsonl_files:
                if jsonl_file not in file_positions:
                    file_positions[jsonl_file] = 0

            # Check each JSONL file for new lines
            for jsonl_file in jsonl_files:
                try:
                    with open(jsonl_file) as f:  # type: ignore[assignment]
                        # Seek to last position
                        f.seek(file_positions[jsonl_file])  # type: ignore[attr-defined]

                        # Read new lines
                        for line in f:  # type: ignore[attr-defined]
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                # Parse JSON and deserialize to event
                                event_data = json.loads(line)
                                event = EventDeserializer.deserialize_event(event_data)

                                if event:
                                    # Emit event to display
                                    await bus.emit(event)
                                    events_found = True

                                    # Check if this is a conversation end event
                                    if (
                                        event.__class__.__name__
                                        == "ConversationEndEvent"
                                    ):
                                        check_for_new_files = True

                            except json.JSONDecodeError:
                                # Skip malformed lines
                                pass
                            except Exception:
                                # Skip events that can't be deserialized
                                pass

                        # Update position
                        file_positions[jsonl_file] = f.tell()  # type: ignore[attr-defined]

                except FileNotFoundError:
                    # File might have been deleted
                    pass
                except Exception:
                    # Other file errors
                    pass

            # Check if experiment is still running
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:  # type: ignore[assignment]
                        manifest = json.load(f)  # type: ignore[arg-type]
                        status = manifest.get("status", "")
                        total_conversations = manifest.get("total_conversations", 0)
                        completed_conversations = manifest.get(
                            "completed_conversations", 0
                        )
                        failed_conversations = manifest.get("failed_conversations", 0)

                        # Check if all conversations are done
                        all_conversations_done = (
                            completed_conversations + failed_conversations
                            >= total_conversations
                        )

                        # Check if experiment is in a terminal state
                        # We now wait for COMPLETED status (not POST_PROCESSING)
                        # because runner.py sets status back to COMPLETED after post-processing
                        terminal_statuses = [
                            "completed",
                            "failed",
                            "interrupted",
                            "cancelled",
                        ]

                        # Only exit if:
                        # 1. Status is terminal (not post_processing)
                        # 2. All conversations are done
                        # 3. We're not in post_processing state
                        if (
                            status in terminal_statuses
                            and all_conversations_done
                            and status != "post_processing"
                        ):
                            # One more pass to catch final events
                            await asyncio.sleep(0.5)
                            continue_reading = False
                            for jsonl_file in jsonl_files:
                                try:
                                    with open(jsonl_file) as f:  # type: ignore[assignment]
                                        f.seek(file_positions[jsonl_file])  # type: ignore[attr-defined]
                                        if f.read(1):  # type: ignore[attr-defined]  # Check if there's more data
                                            continue_reading = True
                                            f.seek(file_positions[jsonl_file])  # type: ignore[attr-defined]
                                except OSError:
                                    pass

                            if not continue_reading:
                                # No more data to read, exit
                                break
                        elif status == "post_processing":
                            # If we're in post_processing, keep waiting
                            logging.debug(
                                "Experiment is in post-processing, continuing to monitor..."
                            )
                            pass
                except Exception:
                    pass

            # Sleep briefly before next check
            if events_found:
                await asyncio.sleep(0.1)  # Short sleep when actively reading
            else:
                await asyncio.sleep(0.5)  # Longer sleep when idle

    except KeyboardInterrupt:
        # Ctrl+C pressed, exit gracefully
        pass
    except Exception as e:
        console.print(f"[red]Display error: {e}[/red]")
