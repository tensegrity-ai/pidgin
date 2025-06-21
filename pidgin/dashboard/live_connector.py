"""Live event connector for real-time dashboard updates."""

import json
import asyncio
from pathlib import Path
from typing import Optional, Set
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..core.event_bus import EventBus
from .event_replayer import EventLogReplayer


class EventLogWatcher(FileSystemEventHandler):
    """Watch event log files for new events."""
    
    def __init__(self, event_bus: EventBus, replayer: EventLogReplayer):
        self.event_bus = event_bus
        self.replayer = replayer
        self.file_positions = {}  # Track read position per file
        self.pending_files = asyncio.Queue()
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.src_path.endswith('events.jsonl'):
            # Queue file for processing
            self.pending_files.put_nowait(event.src_path)
            
    async def process_new_events(self):
        """Process new events from modified files."""
        while True:
            try:
                file_path = await self.pending_files.get()
                await self._read_new_events(file_path)
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue processing even if one file has issues
                pass
                
    async def _read_new_events(self, file_path: str):
        """Read new events from a file."""
        path = Path(file_path)
        if not path.exists():
            return
            
        # Get last read position
        last_pos = self.file_positions.get(file_path, 0)
        
        async with aiofiles.open(file_path, 'r') as f:
            # Seek to last position
            await f.seek(last_pos)
            
            # Read new lines
            while True:
                line = await f.readline()
                if not line:
                    break
                    
                try:
                    event_data = json.loads(line.strip())
                    event = self.replayer._reconstruct_event(event_data)
                    if event:
                        await self.event_bus.emit(event)
                except:
                    pass
                    
            # Update position
            self.file_positions[file_path] = await f.tell()


class LiveEventConnector:
    """Connect dashboard to live events from daemon."""
    
    def __init__(self, experiment_id: str, event_bus: EventBus):
        self.experiment_id = experiment_id
        self.event_bus = event_bus
        self.observer = None
        self.watcher = None
        self.process_task = None
        
    async def start(self):
        """Start watching for new events."""
        # Create event replayer for reconstruction
        replayer = EventLogReplayer(self.experiment_id)
        
        # Create file watcher
        self.watcher = EventLogWatcher(self.event_bus, replayer)
        
        # Start async processing task
        self.process_task = asyncio.create_task(self.watcher.process_new_events())
        
        # Set up file system observer
        self.observer = Observer()
        
        # Watch experiment directory
        watch_dir = Path("pidgin_output") / "experiments" / self.experiment_id
        if watch_dir.exists():
            self.observer.schedule(self.watcher, str(watch_dir), recursive=True)
            self.observer.start()
            
    async def stop(self):
        """Stop watching for events."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            
        if self.process_task:
            self.process_task.cancel()
            try:
                await self.process_task
            except asyncio.CancelledError:
                pass