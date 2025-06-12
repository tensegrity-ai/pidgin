"""Factory for creating configured event system components."""

from pathlib import Path
from typing import Optional

from .config_manager import Config
from .events import EventStore, PrivacyFilter
from .event_transcripts import TranscriptGenerator
from .event_dialogue import EventDialogueEngine
from .router import Router


def create_event_store(config: Config) -> EventStore:
    """Create an EventStore instance from configuration."""
    events_config = config.get_events_config()
    storage_config = config.get_storage_config()
    privacy_config = config.get_privacy_config()
    
    # Resolve data directory
    data_dir_str = storage_config.get('data_dir', '~/.pidgin_data/events')
    data_dir = Path(data_dir_str).expanduser()
    
    # Create privacy filter if enabled
    privacy_filter = None
    if privacy_config.get('enabled', False):
        privacy_filter = PrivacyFilter(
            remove_content=privacy_config.get('remove_content', False),
            hash_models=privacy_config.get('hash_models', False),
            redact_patterns=set(privacy_config.get('redact_patterns', []))
        )
    
    # Create event store
    compression_config = events_config.get('compression', {})
    event_store = EventStore(
        data_dir=data_dir,
        privacy_filter=privacy_filter,
        compress_completed=compression_config.get('compress_on_completion', True)
    )
    
    return event_store


def create_transcript_generator(event_store: EventStore) -> TranscriptGenerator:
    """Create a TranscriptGenerator instance."""
    return TranscriptGenerator(event_store)


def create_event_dialogue_engine(router: Router, event_store: EventStore, config: Config) -> EventDialogueEngine:
    """Create an EventDialogueEngine instance from configuration."""
    return EventDialogueEngine(
        router=router,
        event_store=event_store,
        config=config.to_dict()
    )


def setup_console_subscriber(event_store: EventStore, verbose: bool = False):
    """Set up a console subscriber for real-time event display."""
    from rich.console import Console
    
    console = Console()
    
    def console_subscriber(event):
        """Display relevant events to console in real-time."""
        if not verbose:
            # Only show important events in non-verbose mode
            important_events = {
                'attractor.detected',
                'convergence.measured',
                'response.interrupted',
                'pause.requested',
                'rate_limit.warning',
                'experiment.failed'
            }
            
            if event.type.value not in important_events:
                return
        
        # Format event for display
        if event.type.value == 'attractor.detected':
            console.print(f"[red]🎯 Attractor: {event.data.get('type')}[/red]")
        elif event.type.value == 'convergence.measured':
            score = event.data.get('score', 0)
            if score > 0.8:
                console.print(f"[yellow]📈 High convergence: {score:.2f}[/yellow]")
        elif event.type.value == 'response.interrupted':
            console.print(f"[yellow]⚡ Response interrupted[/yellow]")
        elif event.type.value == 'pause.requested':
            reason = event.data.get('reason', 'unknown')
            console.print(f"[yellow]⏸️ Paused: {reason}[/yellow]")
        elif event.type.value == 'rate_limit.warning':
            console.print(f"[red]⚠️ Rate limit: {event.data.get('message', '')}[/red]")
        elif event.type.value == 'experiment.failed':
            console.print(f"[red]❌ Experiment failed: {event.data.get('error', '')}[/red]")
        elif verbose:
            # In verbose mode, show all events
            console.print(f"[dim]{event.type.value}[/dim]", style="dim")
    
    event_store.subscribe(console_subscriber)
    return console_subscriber


def setup_file_logger(event_store: EventStore, log_path: Optional[Path] = None):
    """Set up a file logger for events."""
    import json
    from datetime import datetime
    
    if log_path is None:
        log_path = Path.home() / ".pidgin_data" / "event_logs" / f"pidgin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def file_logger(event):
        """Log events to file in a structured format."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(event.timestamp).isoformat(),
            'type': event.type.value,
            'experiment_id': event.experiment_id,
            'turn': event.turn_number,
            'agent': event.agent_id,
            'data': event.data
        }
        
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    event_store.subscribe(file_logger)
    return file_logger, log_path


def setup_metrics_collector(event_store: EventStore):
    """Set up a metrics collector for monitoring."""
    metrics = {
        'experiments_started': 0,
        'experiments_completed': 0,
        'experiments_failed': 0,
        'total_turns': 0,
        'total_interruptions': 0,
        'attractors_detected': 0,
        'api_failures': 0
    }
    
    def metrics_collector(event):
        """Collect metrics from events."""
        if event.type.value == 'experiment.started':
            metrics['experiments_started'] += 1
        elif event.type.value == 'experiment.completed':
            metrics['experiments_completed'] += 1
        elif event.type.value == 'experiment.failed':
            metrics['experiments_failed'] += 1
        elif event.type.value == 'turn.completed':
            metrics['total_turns'] += 1
        elif event.type.value == 'response.interrupted':
            metrics['total_interruptions'] += 1
        elif event.type.value == 'attractor.detected':
            metrics['attractors_detected'] += 1
        elif event.type.value == 'api.call.failed':
            metrics['api_failures'] += 1
    
    event_store.subscribe(metrics_collector)
    return metrics, metrics_collector


def get_event_summary(event_store: EventStore, experiment_id: str) -> dict:
    """Get a comprehensive summary of an experiment."""
    # Get database summary
    db_summary = event_store.get_experiment_summary(experiment_id)
    
    # Get additional details from queries
    convergence_trend = event_store.query_convergence_trend(experiment_id)
    interruptions = event_store.query_interruptions(experiment_id)
    attractors = event_store.query_attractors(experiment_id)
    
    # Replay events for additional analysis
    events = event_store.replay_experiment(experiment_id)
    
    # Calculate additional metrics
    start_event = next((e for e in events if e.type.value == 'experiment.started'), None)
    end_event = next((e for e in events if e.type.value in ['experiment.completed', 'experiment.failed']), None)
    
    response_events = [e for e in events if e.type.value == 'response.completed']
    total_tokens = sum(e.data.get('tokens', 0) for e in response_events)
    avg_response_time = sum(e.data.get('duration', 0) for e in response_events) / len(response_events) if response_events else 0
    
    return {
        **db_summary,
        'start_time': start_event.timestamp if start_event else None,
        'end_time': end_event.timestamp if end_event else None,
        'convergence_trend': convergence_trend,
        'interruptions': interruptions,
        'attractors': attractors,
        'total_tokens': total_tokens,
        'avg_response_time': avg_response_time,
        'events_count': len(events)
    }