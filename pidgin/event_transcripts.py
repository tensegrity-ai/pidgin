"""Generate transcripts and exports from event streams."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .events import Event, EventType, EventStore


class TranscriptGenerator:
    """Generate transcripts from event streams."""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    def generate_markdown(self, experiment_id: str) -> str:
        """Generate human-readable transcript from events."""
        events = self.event_store.replay_experiment(experiment_id)
        
        if not events:
            return "# No events found"
        
        lines = ["# Pidgin Conversation Transcript\n"]
        
        # Extract metadata from start event
        start_event = next((e for e in events if e.type == EventType.EXPERIMENT_STARTED), None)
        if start_event:
            lines.append(f"**Date**: {datetime.fromtimestamp(start_event.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"**Experiment ID**: {experiment_id}")
            lines.append(f"**Models**: {start_event.data.get('model_a')} ↔ {start_event.data.get('model_b')}")
            lines.append(f"**Initial Prompt**: {start_event.data.get('initial_prompt')}")
            lines.append(f"**Max Turns**: {start_event.data.get('max_turns')}")
            lines.append("\n---\n")
        
        # Process conversation events
        current_turn = None
        for event in events:
            if event.type == EventType.TURN_STARTED:
                current_turn = event.turn_number
                lines.append(f"\n## Turn {current_turn}\n")
                
            elif event.type == EventType.RESPONSE_COMPLETED:
                agent = "Agent A" if event.agent_id == "agent_a" else "Agent B"
                model = event.data.get('model', '')
                if model:
                    agent = f"{agent} ({model})"
                lines.append(f"**{agent}**: {event.data.get('content', '')}\n")
                
                # Add metrics if available
                duration = event.data.get('duration')
                tokens = event.data.get('tokens')
                if duration or tokens:
                    metrics = []
                    if duration:
                        metrics.append(f"{duration:.1f}s")
                    if tokens:
                        metrics.append(f"{tokens} tokens")
                    lines.append(f"*[{', '.join(metrics)}]*\n")
                
            elif event.type == EventType.RESPONSE_INTERRUPTED:
                lines.append(f"*[Response interrupted after {event.data.get('chars_received', 0)} characters ({event.data.get('duration', 0):.1f}s)]*\n")
                
            elif event.type == EventType.CONDUCTOR_INTERVENTION:
                source = event.data.get('source', 'Conductor')
                lines.append(f"**{source}**: {event.data.get('content', '')}\n")
                
            elif event.type == EventType.ATTRACTOR_DETECTED:
                lines.append(f"\n> 🎯 **Attractor Detected**: {event.data.get('type')} (confidence: {event.data.get('confidence', 0):.0%})")
                lines.append(f"> {event.data.get('description', '')}\n")
                
            elif event.type == EventType.CONVERGENCE_MEASURED:
                score = event.data.get('score', 0)
                if score >= 0.9:
                    lines.append(f"\n> ⚠️ **High Convergence**: {score:.2f}\n")
                    
            elif event.type == EventType.PAUSE_REQUESTED:
                lines.append(f"\n> ⏸️ **Conversation Paused**\n")
                
            elif event.type == EventType.CONVERSATION_RESUMED:
                lines.append(f"\n> ▶️ **Conversation Resumed**\n")
                
            elif event.type == EventType.RATE_LIMIT_WARNING:
                lines.append(f"\n> ⚠️ **Rate Limit**: {event.data.get('message', 'API rate limit reached')}\n")
        
        # Add summary statistics
        lines.append("\n---\n\n## Summary\n")
        lines.extend(self._generate_summary(events, experiment_id))
        
        return "\n".join(lines)
    
    def _generate_summary(self, events: List[Event], experiment_id: str) -> List[str]:
        """Generate summary statistics from events."""
        lines = []
        
        # Get summary from database
        summary = self.event_store.get_experiment_summary(experiment_id)
        
        # Basic stats
        lines.append(f"- **Total Turns**: {summary['turns']}")
        lines.append(f"- **Duration**: {summary['duration']:.1f} seconds")
        lines.append(f"- **Total Events**: {summary['total_events']}")
        
        # Interruptions
        if summary['interruptions'] > 0:
            lines.append(f"- **Interruptions**: {summary['interruptions']}")
        
        # Attractors
        if summary['attractors'] > 0:
            lines.append(f"- **Attractors Detected**: {summary['attractors']}")
            
        # Convergence
        if summary['max_convergence'] > 0:
            lines.append(f"- **Max Convergence**: {summary['max_convergence']:.2f}")
        
        # Token usage
        token_events = [e for e in events if e.type == EventType.RESPONSE_COMPLETED and 'tokens' in e.data]
        if token_events:
            total_tokens = sum(e.data['tokens'] for e in token_events)
            lines.append(f"- **Total Tokens**: {total_tokens:,}")
        
        # Completion status
        completion_event = next((e for e in events if e.type == EventType.EXPERIMENT_COMPLETED), None)
        if completion_event:
            lines.append(f"- **Status**: ✅ Completed")
        else:
            failure_event = next((e for e in events if e.type == EventType.EXPERIMENT_FAILED), None)
            if failure_event:
                lines.append(f"- **Status**: ❌ Failed - {failure_event.data.get('error', 'Unknown error')}")
            else:
                lines.append(f"- **Status**: ⚠️ Incomplete")
        
        return lines
    
    def generate_json(self, experiment_id: str) -> Dict[str, Any]:
        """Generate machine-readable format from events."""
        events = self.event_store.replay_experiment(experiment_id)
        
        # Reconstruct conversation state
        conversation = {
            'id': experiment_id,
            'metadata': {},
            'messages': [],
            'interventions': [],
            'events': [],
            'metrics': {
                'turns': 0,
                'total_tokens': 0,
                'interruptions': 0,
                'attractors': [],
                'convergence_history': [],
                'context_usage': []
            }
        }
        
        for event in events:
            # Add to event log
            conversation['events'].append({
                'type': event.type.value,
                'timestamp': event.timestamp,
                'turn': event.turn_number,
                'agent': event.agent_id,
                'data': event.data
            })
            
            # Process specific event types
            if event.type == EventType.EXPERIMENT_STARTED:
                conversation['metadata'] = event.data
                
            elif event.type == EventType.RESPONSE_COMPLETED:
                conversation['messages'].append({
                    'turn': event.turn_number,
                    'agent': event.agent_id,
                    'content': event.data.get('content'),
                    'tokens': event.data.get('tokens'),
                    'duration': event.data.get('duration'),
                    'timestamp': event.timestamp
                })
                conversation['metrics']['total_tokens'] += event.data.get('tokens', 0)
                conversation['metrics']['turns'] = max(conversation['metrics']['turns'], event.turn_number or 0)
                
            elif event.type == EventType.RESPONSE_INTERRUPTED:
                conversation['metrics']['interruptions'] += 1
                # Still add the partial message
                conversation['messages'].append({
                    'turn': event.turn_number,
                    'agent': event.agent_id,
                    'content': event.data.get('content', ''),
                    'interrupted': True,
                    'chars_received': event.data.get('chars_received'),
                    'timestamp': event.timestamp
                })
                
            elif event.type == EventType.CONDUCTOR_INTERVENTION:
                conversation['interventions'].append({
                    'turn': event.turn_number,
                    'source': event.data.get('source'),
                    'content': event.data.get('content'),
                    'timestamp': event.timestamp
                })
                
            elif event.type == EventType.ATTRACTOR_DETECTED:
                conversation['metrics']['attractors'].append({
                    'turn': event.turn_number,
                    'type': event.data.get('type'),
                    'confidence': event.data.get('confidence'),
                    'description': event.data.get('description')
                })
                
            elif event.type == EventType.CONVERGENCE_MEASURED:
                conversation['metrics']['convergence_history'].append({
                    'turn': event.turn_number,
                    'score': event.data.get('score'),
                    'timestamp': event.timestamp
                })
                
            elif event.type == EventType.CONTEXT_USAGE:
                conversation['metrics']['context_usage'].append({
                    'turn': event.turn_number,
                    'agent': event.agent_id,
                    'percentage': event.data.get('percentage'),
                    'tokens_used': event.data.get('tokens_used'),
                    'tokens_remaining': event.data.get('tokens_remaining')
                })
        
        # Add summary
        conversation['summary'] = self.event_store.get_experiment_summary(experiment_id)
        
        return conversation
    
    def export_for_analysis(self, experiment_id: str, output_path: Optional[Path] = None, 
                          format: str = 'parquet') -> Path:
        """Export events in data science friendly format."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for data export. Install with: pip install pandas")
        
        events = self.event_store.replay_experiment(experiment_id)
        
        # Convert to DataFrame
        records = []
        for event in events:
            record = {
                'event_id': event.id,
                'type': event.type.value,
                'timestamp': event.timestamp,
                'datetime': datetime.fromtimestamp(event.timestamp),
                'turn': event.turn_number,
                'agent': event.agent_id,
                'experiment_id': event.experiment_id
            }
            
            # Flatten certain data fields for easier analysis
            if event.type == EventType.RESPONSE_COMPLETED:
                record['content_length'] = event.data.get('length', 0)
                record['tokens'] = event.data.get('tokens', 0)
                record['duration'] = event.data.get('duration', 0)
            elif event.type == EventType.CONVERGENCE_MEASURED:
                record['convergence_score'] = event.data.get('score', 0)
            elif event.type == EventType.ATTRACTOR_DETECTED:
                record['attractor_type'] = event.data.get('type')
                record['attractor_confidence'] = event.data.get('confidence')
                
            # Keep full data as JSON string for flexibility
            record['data_json'] = json.dumps(event.data)
            
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Set proper data types
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['timestamp'] = df['timestamp'].astype(float)
            if 'turn' in df.columns:
                df['turn'] = df['turn'].fillna(-1).astype(int)
        
        # Determine output path
        if output_path is None:
            output_path = self.event_store.data_dir / f"{experiment_id}.{format}"
        
        # Export based on format
        if format == 'parquet':
            df.to_parquet(output_path, index=False)
        elif format == 'csv':
            df.to_csv(output_path, index=False)
        elif format == 'json':
            df.to_json(output_path, orient='records', lines=True)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return output_path
    
    def generate_timeline_html(self, experiment_id: str) -> str:
        """Generate an interactive HTML timeline visualization."""
        events = self.event_store.replay_experiment(experiment_id)
        
        if not events:
            return "<h1>No events found</h1>"
        
        # Simple HTML template with inline CSS/JS
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Pidgin Timeline - {experiment_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        .timeline {{ position: relative; padding: 20px 0; }}
        .event {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ccc; }}
        .event.experiment {{ border-color: #4CAF50; }}
        .event.response {{ border-color: #2196F3; }}
        .event.intervention {{ border-color: #FF9800; }}
        .event.detection {{ border-color: #f44336; }}
        .event-time {{ color: #666; font-size: 0.9em; }}
        .event-data {{ margin-top: 5px; color: #333; }}
        .turn-marker {{ font-weight: bold; margin: 20px 0 10px 0; color: #333; }}
    </style>
</head>
<body>
    <h1>Pidgin Experiment Timeline</h1>
    <p><strong>Experiment ID:</strong> {experiment_id}</p>
    <div class="timeline">
"""
        
        current_turn = -1
        start_time = events[0].timestamp if events else 0
        
        for event in events:
            # Add turn markers
            if event.turn_number is not None and event.turn_number != current_turn:
                current_turn = event.turn_number
                html += f'<div class="turn-marker">Turn {current_turn}</div>\n'
            
            # Determine event category for styling
            category = 'event'
            if 'experiment' in event.type.value:
                category = 'experiment'
            elif 'response' in event.type.value:
                category = 'response'
            elif 'intervention' in event.type.value or 'pause' in event.type.value:
                category = 'intervention'
            elif 'detected' in event.type.value or 'measured' in event.type.value:
                category = 'detection'
            
            # Format event
            elapsed = event.timestamp - start_time
            time_str = datetime.fromtimestamp(event.timestamp).strftime('%H:%M:%S.%f')[:-3]
            
            html += f'<div class="event {category}">\n'
            html += f'  <div class="event-time">{time_str} (+{elapsed:.1f}s)</div>\n'
            html += f'  <strong>{event.type.value}</strong>'
            
            if event.agent_id:
                html += f' - {event.agent_id}'
                
            # Add key data points
            if event.type == EventType.RESPONSE_COMPLETED:
                length = event.data.get('length', 0)
                tokens = event.data.get('tokens', 0)
                html += f'<div class="event-data">{length} chars, {tokens} tokens</div>'
            elif event.type == EventType.CONVERGENCE_MEASURED:
                score = event.data.get('score', 0)
                html += f'<div class="event-data">Score: {score:.3f}</div>'
            elif event.type == EventType.ATTRACTOR_DETECTED:
                html += f'<div class="event-data">Type: {event.data.get("type")} ({event.data.get("confidence", 0):.0%})</div>'
                
            html += '</div>\n'
        
        html += """
    </div>
</body>
</html>
"""
        return html