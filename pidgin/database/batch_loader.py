"""Batch loader for loading JSONL events into DuckDB after experiments complete."""

import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .event_store import EventStore
from ..io.logger import get_logger

logger = get_logger("batch_loader")


class BatchLoader:
    """Load completed experiment data from JSONL into DuckDB for analytics."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize batch loader.
        
        Args:
            db_path: Path to DuckDB database
        """
        self.store = EventStore(db_path=db_path, read_only=False)
        
    async def load_experiment(self, exp_dir: Path) -> bool:
        """Load a single experiment's JSONL data into DuckDB.
        
        Args:
            exp_dir: Path to experiment directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure database is initialized
            await self.store.initialize()
            
            logger.info(f"Loading experiment from {exp_dir}")
            
            # Find all JSONL files in experiment
            jsonl_files = list(exp_dir.glob("*_events.jsonl"))
            if not jsonl_files:
                logger.warning(f"No JSONL files found in {exp_dir}")
                return False
            
            # Process each JSONL file
            total_events = 0
            for jsonl_file in jsonl_files:
                events_loaded = await self._load_jsonl_file(jsonl_file)
                total_events += events_loaded
                
            logger.info(f"Loaded {total_events} events from {len(jsonl_files)} files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load experiment {exp_dir}: {e}")
            return False
    
    async def _load_jsonl_file(self, jsonl_path: Path) -> int:
        """Load events from a single JSONL file.
        
        Args:
            jsonl_path: Path to JSONL file
            
        Returns:
            Number of events loaded
        """
        events_loaded = 0
        
        try:
            with open(jsonl_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                        
                    try:
                        event_data = json.loads(line)
                        
                        # Extract event info
                        event_type = event_data.get('event_type', 'Unknown')
                        conversation_id = event_data.get('conversation_id')
                        experiment_id = event_data.get('experiment_id')
                        
                        # Skip if missing required fields
                        if not event_type:
                            logger.warning(f"Skipping event without type at {jsonl_path}:{line_num}")
                            continue
                        
                        # Emit to database
                        await self.store.emit_event(
                            event_type=event_type,
                            conversation_id=conversation_id,
                            experiment_id=experiment_id,
                            data=event_data
                        )
                        
                        events_loaded += 1
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON at {jsonl_path}:{line_num}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing event at {jsonl_path}:{line_num}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to read {jsonl_path}: {e}")
            
        return events_loaded
    
    async def load_completed_experiments(self, base_dir: Path) -> dict:
        """Load all completed experiments that haven't been loaded yet.
        
        Args:
            base_dir: Base directory containing experiments
            
        Returns:
            Dictionary with statistics about loading
        """
        stats = {
            'total_experiments': 0,
            'loaded': 0,
            'failed': 0,
            'already_loaded': 0
        }
        
        try:
            await self.store.initialize()
            
            # Find all experiment directories
            for exp_dir in base_dir.glob("exp_*"):
                if not exp_dir.is_dir():
                    continue
                    
                stats['total_experiments'] += 1
                
                # Check if already loaded by looking for marker file
                marker_file = exp_dir / ".loaded_to_db"
                if marker_file.exists():
                    stats['already_loaded'] += 1
                    continue
                
                # Check if experiment is complete by looking for completion marker
                # or by checking state from JSONL
                from ..experiments.state_builder import StateBuilder
                state = StateBuilder.from_experiment_dir(exp_dir)
                
                if not state or state.status not in ['completed', 'failed', 'interrupted']:
                    logger.info(f"Skipping {exp_dir.name} - status: {state.status if state else 'unknown'}")
                    continue
                
                # Load the experiment
                logger.info(f"Loading completed experiment {exp_dir.name}")
                if await self.load_experiment(exp_dir):
                    # Create marker file
                    marker_file.touch()
                    stats['loaded'] += 1
                else:
                    stats['failed'] += 1
                    
        except Exception as e:
            logger.error(f"Batch loading failed: {e}")
            
        finally:
            await self.store.close()
            
        return stats
    
    async def close(self):
        """Close database connections."""
        await self.store.close()


async def main():
    """CLI entry point for batch loading."""
    import sys
    from ..io.paths import get_experiments_dir
    
    if len(sys.argv) > 1:
        # Load specific experiment
        exp_path = Path(sys.argv[1])
        loader = BatchLoader()
        try:
            success = await loader.load_experiment(exp_path)
            if success:
                print(f"Successfully loaded {exp_path}")
            else:
                print(f"Failed to load {exp_path}")
                sys.exit(1)
        finally:
            await loader.close()
    else:
        # Load all completed experiments
        loader = BatchLoader()
        try:
            stats = await loader.load_completed_experiments(get_experiments_dir())
            print(f"\nBatch loading complete:")
            print(f"  Total experiments: {stats['total_experiments']}")
            print(f"  Newly loaded: {stats['loaded']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Already loaded: {stats['already_loaded']}")
        finally:
            await loader.close()


if __name__ == "__main__":
    asyncio.run(main())