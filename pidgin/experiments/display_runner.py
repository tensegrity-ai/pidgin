"""Display runner that tails JSONL files and shows live updates."""

import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from rich.console import Console
from ..ui.tail_display import TailDisplay
from ..ui.verbose_display import VerboseDisplay
from ..core.event_bus import EventBus
from ..io.event_deserializer import EventDeserializer
from ..io.paths import get_experiments_dir
from ..core.types import Agent

console = Console()


async def run_display(experiment_id: str, display_mode: str = 'tail'):
    """Run live display by tailing JSONL files.
    
    Args:
        experiment_id: The experiment ID to display
        display_mode: Display mode ('tail', 'verbose', or 'none')
    """
    if display_mode == 'none':
        return
        
    exp_dir = get_experiments_dir() / experiment_id
    if not exp_dir.exists():
        console.print(f"[red]Experiment directory not found: {exp_dir}[/red]")
        return
    
    # Create event bus and display
    bus = EventBus()
    
    if display_mode == 'verbose':
        # For verbose display, we need to create dummy agents
        # In the future, we could read this from manifest
        agents = {
            "agent_a": Agent(id="agent_a", model="unknown", display_name="Agent A"),
            "agent_b": Agent(id="agent_b", model="unknown", display_name="Agent B")
        }
        display = VerboseDisplay(bus, console, agents)
    else:
        # Default to tail display
        display = TailDisplay(bus, console)
    
    # Track file positions
    file_positions = {}
    
    # Get initial JSONL files
    jsonl_files = list(exp_dir.glob("*.jsonl"))
    
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
                    with open(jsonl_file, 'r') as f:
                        # Seek to last position
                        f.seek(file_positions[jsonl_file])
                        
                        # Read new lines
                        for line in f:
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
                                    if event.__class__.__name__ == 'ConversationEndEvent':
                                        check_for_new_files = True
                                    
                            except json.JSONDecodeError:
                                # Skip malformed lines
                                pass
                            except Exception as e:
                                # Skip events that can't be deserialized
                                pass
                        
                        # Update position
                        file_positions[jsonl_file] = f.tell()
                        
                except FileNotFoundError:
                    # File might have been deleted
                    pass
                except Exception as e:
                    # Other file errors
                    pass
            
            # Check if experiment is still running
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                        status = manifest.get('status', '')
                        total_conversations = manifest.get('total_conversations', 0)
                        completed_conversations = manifest.get('completed_conversations', 0)
                        failed_conversations = manifest.get('failed_conversations', 0)
                        
                        # Check if all conversations are done
                        all_conversations_done = (completed_conversations + failed_conversations >= total_conversations)
                        
                        # Only exit if experiment is complete AND all conversations are done
                        if status in ['completed', 'failed'] and all_conversations_done:
                            # One more pass to catch final events
                            await asyncio.sleep(0.5)
                            continue_reading = False
                            for jsonl_file in jsonl_files:
                                try:
                                    with open(jsonl_file, 'r') as f:
                                        f.seek(file_positions[jsonl_file])
                                        if f.read(1):  # Check if there's more data
                                            continue_reading = True
                                            f.seek(file_positions[jsonl_file])
                                except:
                                    pass
                            
                            if not continue_reading:
                                # No more data to read, exit
                                break
                except:
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