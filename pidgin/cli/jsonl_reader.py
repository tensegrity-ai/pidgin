"""Read experiment data from JSONL event files."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

from ..io.logger import get_logger

logger = get_logger("jsonl_reader")


class JSONLExperimentReader:
    """Read experiment data from JSONL event files."""
    
    def __init__(self, experiments_dir: Path):
        """Initialize reader with experiments directory.
        
        Args:
            experiments_dir: Base directory containing experiments
        """
        self.experiments_dir = Path(experiments_dir)
    
    def list_experiments(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all experiments by scanning JSONL files.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of experiment dictionaries
        """
        experiments = {}
        
        # Scan for experiment directories
        for exp_dir in self.experiments_dir.iterdir():
            if not exp_dir.is_dir() or not exp_dir.name.startswith('exp_'):
                continue
                
            # Look for events directory
            events_dir = exp_dir / "events"
            if not events_dir.exists():
                continue
            
            # Parse JSONL files to get experiment info
            exp_info = self._parse_experiment_from_events(exp_dir.name, events_dir)
            if exp_info:
                if status_filter is None or exp_info.get('status') == status_filter:
                    experiments[exp_info['experiment_id']] = exp_info
        
        # Sort by created_at descending
        return sorted(
            experiments.values(), 
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
    
    def get_experiment_status(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a specific experiment.
        
        Args:
            experiment_id: Experiment ID to look up
            
        Returns:
            Experiment info dict or None if not found
        """
        exp_dir = self.experiments_dir / experiment_id
        if not exp_dir.exists():
            return None
            
        events_dir = exp_dir / "events"
        if not events_dir.exists():
            return None
            
        return self._parse_experiment_from_events(experiment_id, events_dir)
    
    def _parse_experiment_from_events(self, experiment_id: str, events_dir: Path) -> Optional[Dict[str, Any]]:
        """Parse experiment info from JSONL event files.
        
        Args:
            experiment_id: Experiment ID
            events_dir: Directory containing JSONL files
            
        Returns:
            Experiment info dict
        """
        # Aggregate data from all conversation event files
        conversations = {}
        experiment_info = {
            'experiment_id': experiment_id,
            'status': 'unknown',
            'created_at': None,
            'started_at': None,
            'completed_conversations': 0,
            'failed_conversations': 0,
            'total_conversations': 0,
            'config': {},
            'name': experiment_id  # Default to ID if no name found
        }
        
        # Process each JSONL file
        for jsonl_file in events_dir.glob("*.jsonl"):
            conv_id = jsonl_file.stem.replace('_events', '')
            conv_info = self._parse_conversation_events(jsonl_file)
            
            if conv_info:
                conversations[conv_id] = conv_info
                
                # Update experiment info from first conversation
                if not experiment_info['created_at'] and conv_info.get('started_at'):
                    experiment_info['created_at'] = conv_info['started_at']
                    experiment_info['started_at'] = conv_info['started_at']
                
                # Extract config from first conversation
                if not experiment_info['config'] and conv_info.get('config'):
                    experiment_info['config'] = conv_info['config']
                    # Try to extract name from initial prompt
                    if 'initial_prompt' in conv_info['config']:
                        experiment_info['name'] = self._extract_name_from_prompt(
                            conv_info['config']['initial_prompt']
                        )
                
                # Count conversation statuses
                if conv_info['status'] == 'completed':
                    experiment_info['completed_conversations'] += 1
                elif conv_info['status'] == 'failed':
                    experiment_info['failed_conversations'] += 1
        
        # Calculate total conversations and overall status
        experiment_info['total_conversations'] = len(conversations)
        
        if experiment_info['total_conversations'] == 0:
            return None
            
        # Determine experiment status
        if experiment_info['completed_conversations'] + experiment_info['failed_conversations'] == experiment_info['total_conversations']:
            experiment_info['status'] = 'completed'
        elif any(c['status'] == 'running' for c in conversations.values()):
            experiment_info['status'] = 'running'
        else:
            experiment_info['status'] = 'unknown'
        
        return experiment_info
    
    def _parse_conversation_events(self, jsonl_file: Path) -> Optional[Dict[str, Any]]:
        """Parse a single conversation's events.
        
        Args:
            jsonl_file: Path to JSONL file
            
        Returns:
            Conversation info dict
        """
        conv_info = {
            'status': 'unknown',
            'started_at': None,
            'ended_at': None,
            'total_turns': 0,
            'config': {},
            'convergence_scores': []
        }
        
        try:
            with open(jsonl_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    try:
                        event = json.loads(line)
                        event_type = event.get('event_type')
                        
                        if event_type == 'ConversationStartEvent':
                            conv_info['started_at'] = event.get('timestamp')
                            conv_info['status'] = 'running'
                            # Extract config
                            conv_info['config'] = {
                                'agent_a_model': event.get('agent_a_model'),
                                'agent_b_model': event.get('agent_b_model'),
                                'initial_prompt': event.get('initial_prompt'),
                                'max_turns': event.get('max_turns'),
                                'temperature_a': event.get('temperature_a'),
                                'temperature_b': event.get('temperature_b')
                            }
                        
                        elif event_type == 'ConversationEndEvent':
                            conv_info['ended_at'] = event.get('timestamp')
                            conv_info['total_turns'] = event.get('total_turns', 0)
                            reason = event.get('reason', '')
                            
                            if reason == 'max_turns' or reason == 'high_convergence':
                                conv_info['status'] = 'completed'
                            elif reason == 'error':
                                conv_info['status'] = 'failed'
                            else:
                                conv_info['status'] = 'interrupted'
                        
                        elif event_type == 'TurnCompleteEvent':
                            conv_info['total_turns'] = max(
                                conv_info['total_turns'], 
                                event.get('turn_number', 0)
                            )
                            if 'convergence_score' in event:
                                conv_info['convergence_scores'].append(event['convergence_score'])
                                
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in {jsonl_file}: {line}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading {jsonl_file}: {e}")
            return None
            
        return conv_info
    
    def _extract_name_from_prompt(self, prompt: str) -> str:
        """Try to extract a meaningful name from the initial prompt.
        
        Args:
            prompt: Initial prompt text
            
        Returns:
            Extracted name or truncated prompt
        """
        # Simple heuristic: use first few words
        words = prompt.split()[:5]
        name = ' '.join(words)
        
        # Truncate if too long
        if len(name) > 50:
            name = name[:47] + "..."
            
        return name