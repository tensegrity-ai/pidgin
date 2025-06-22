# pidgin/dashboard/attach.py
"""Attachment logic for dashboard to running experiments."""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from ..experiments.shared_state import SharedState
from ..experiments.storage import ExperimentStore


async def attach_to_experiment(experiment_id: str) -> Dict[str, Any]:
    """Attach to a running experiment with smart retry logic.
    
    Args:
        experiment_id: ID of the experiment to attach to
        
    Returns:
        Dict with:
            - success: True if attached successfully
            - shared_state: SharedState instance if successful
            - experiment_id: The experiment ID
            - error: Error message if failed
    """
    max_retries = 20  # 10 seconds total
    retry_delay = 0.5
    
    # Get database to verify experiment exists
    storage = ExperimentStore()
    
    # First check if experiment exists in database
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        return {
            'success': False,
            'error': f"Experiment {experiment_id} not found in database"
        }
    
    # Check experiment status
    db_status = experiment.get('status', 'unknown')
    if db_status in ['completed', 'failed']:
        return {
            'success': False,
            'error': f"Experiment {experiment_id} already {db_status}"
        }
    
    # Now try to attach to SharedState with retries
    shared_state = None
    last_status = None
    
    for i in range(max_retries):
        try:
            # Try to open SharedState (don't create, just attach)
            shared_state = SharedState(experiment_id, create=False)
            
            # Check if it's ready
            status = shared_state.get_status()
            
            if status != last_status:
                # Status changed, show update
                if status == 'initializing':
                    print(f"Experiment {experiment_id} is initializing...")
                elif status == 'running':
                    print(f"Attached to experiment {experiment_id}")
                last_status = status
            
            if status == 'initializing':
                # Still initializing, wait a bit
                await asyncio.sleep(retry_delay)
                continue
                
            # SharedState exists and is ready (running, completed, or failed)
            return {
                'success': True,
                'shared_state': shared_state,
                'experiment_id': experiment_id,
                'status': status
            }
            
        except FileNotFoundError:
            # SharedState doesn't exist yet
            if i == 0:
                print(f"Waiting for experiment {experiment_id} to start...")
            elif i % 4 == 0:  # Show progress every 2 seconds
                print(f"Still waiting... ({i * retry_delay:.0f}s)")
            
            await asyncio.sleep(retry_delay)
            continue
        except Exception as e:
            # Some other error
            return {
                'success': False,
                'error': f"Error attaching to experiment: {str(e)}"
            }
    
    # Timeout - check database status one more time
    experiment = storage.get_experiment(experiment_id)
    db_status = experiment.get('status', 'unknown') if experiment else 'unknown'
    
    return {
        'success': False,
        'error': f"Timeout waiting for experiment {experiment_id} to start. "
                f"Database status: {db_status}. "
                f"The daemon may have failed to start."
    }


def find_running_experiments() -> list:
    """Find all experiments that appear to be running.
    
    Returns:
        List of experiment IDs that have active SharedState
    """
    running = []
    
    # Check /dev/shm for pidgin_* files
    shm_path = Path("/dev/shm")
    if shm_path.exists():
        for shm_file in shm_path.glob("pidgin_*"):
            # Extract experiment ID from filename
            exp_id = shm_file.name.replace("pidgin_", "")
            
            try:
                # Try to attach to verify it's valid
                shared_state = SharedState(exp_id, create=False)
                status = shared_state.get_status()
                
                if status in ['initializing', 'running']:
                    running.append(exp_id)
                    
            except Exception:
                # Invalid or stale SharedState
                pass
    
    return running


async def wait_for_any_experiment(timeout: float = 30.0) -> Optional[str]:
    """Wait for any experiment to start running.
    
    Args:
        timeout: Maximum time to wait in seconds
        
    Returns:
        Experiment ID if one starts, None if timeout
    """
    start_time = asyncio.get_event_loop().time()
    check_interval = 0.5
    
    print("Waiting for an experiment to start...")
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        running = find_running_experiments()
        
        if running:
            # Found at least one running experiment
            exp_id = running[0]
            print(f"Found running experiment: {exp_id}")
            return exp_id
        
        await asyncio.sleep(check_interval)
    
    print("No experiments started within timeout period")
    return None
