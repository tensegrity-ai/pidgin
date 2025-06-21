"""Dashboard attachment functionality."""

import asyncio
from typing import Dict, Any

from ..core.event_bus import EventBus
from .phase3_dashboard import Phase3Dashboard
from .event_replayer import EventLogReplayer
from .live_connector import LiveEventConnector


async def attach_dashboard_to_experiment(experiment_id: str, experiment_name: str) -> Dict[str, Any]:
    """Attach a dashboard to a running daemon experiment."""
    
    # Create event bus for dashboard
    event_bus = EventBus()
    await event_bus.start()
    
    # Create event replayer to catch up dashboard
    replayer = EventLogReplayer(experiment_id)
    
    # Replay recent events to catch up dashboard state
    await replayer.replay_recent_events(event_bus, last_n_turns=5)
    
    # Create dashboard
    dashboard = Phase3Dashboard(event_bus, experiment_id)
    
    # Connect to live event stream from daemon
    live_connector = LiveEventConnector(experiment_id, event_bus)
    await live_connector.start()
    
    try:
        # Run dashboard
        result = await dashboard.run()
    finally:
        # Clean up connections
        await live_connector.stop()
        await event_bus.stop()
    
    return result