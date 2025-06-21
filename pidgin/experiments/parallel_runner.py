"""Parallel experiment runner with rate limiting."""

import asyncio
import logging
from typing import Dict, Optional

from .runner import ExperimentRunner
from .config import ExperimentConfig
from .storage import ExperimentStore
from .daemon import ExperimentDaemon


class ParallelExperimentRunner(ExperimentRunner):
    """Runs experiments with parallel conversation execution."""
    
    def __init__(self, storage: ExperimentStore, daemon: Optional[ExperimentDaemon] = None):
        """Initialize parallel runner.
        
        Args:
            storage: Database storage
            daemon: Optional daemon for background execution
        """
        super().__init__(storage)
        self.daemon = daemon
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_count = 0
        self.failed_count = 0
        
    def calculate_parallelism(self, config: ExperimentConfig) -> int:
        """Return parallelism level from config - no auto-calculation.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Number of parallel conversations (1 = sequential)
        """
        return config.max_parallel
        
            
    async def run_experiment_with_id(self, experiment_id: str, config: ExperimentConfig) -> str:
        """Run experiment with parallel execution using existing experiment ID.
        
        Args:
            experiment_id: Existing experiment ID
            config: Experiment configuration
            
        Returns:
            Experiment ID
        """
        # Update status to running
        self.storage.update_experiment_status(experiment_id, 'running')
        
        # Continue with the existing logic
        return await self._run_experiment_internal(experiment_id, config)
    
    async def run_experiment(self, config: ExperimentConfig) -> str:
        """Run experiment with parallel execution.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Experiment ID
        """
        experiment_id = self.storage.create_experiment(config.name, config.dict())
        self.storage.update_experiment_status(experiment_id, 'running')
        
        # Continue with the existing logic
        return await self._run_experiment_internal(experiment_id, config)
    
    async def _run_experiment_internal(self, experiment_id: str, config: ExperimentConfig) -> str:
        """Internal method to run experiment with given ID.
        
        Args:
            experiment_id: Experiment ID
            config: Experiment configuration
            
        Returns:
            Experiment ID
        """
        
        # Calculate parallelism
        max_parallel = self.calculate_parallelism(config)
        if max_parallel == 1:
            logging.info(f"Starting experiment {experiment_id} with sequential execution")
        else:
            logging.info(f"Starting experiment {experiment_id} with {max_parallel} parallel conversations")
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_parallel)
        
        # Generate all conversation configs
        conversations = []
        for i in range(config.repetitions):
            conv_config = config.get_conversation_config(i)
            conv_id = f"{experiment_id}_conv_{i:04d}"
            # Create conversation record
            self.storage.create_conversation(experiment_id, conv_id, conv_config)
            conversations.append((conv_id, conv_config))
            
        # Progress tracking
        self.completed_count = 0
        self.failed_count = 0
        total = len(conversations)
        
        async def run_with_semaphore(conv_id: str, conv_config: dict):
            """Run single conversation with semaphore control."""
            async with semaphore:
                # Check if daemon wants to stop
                if self.daemon and self.daemon.is_stopping():
                    logging.info(f"Skipping {conv_id} due to stop request")
                    return
                    
                try:
                    logging.info(f"Starting {conv_id}")
                    await self._run_single_conversation(
                        experiment_id, conv_id, config, conv_config
                    )
                    self.completed_count += 1
                    logging.info(f"Completed {conv_id} ({self.completed_count}/{total})")
                except asyncio.CancelledError:
                    # Handle graceful cancellation
                    logging.info(f"Cancelled {conv_id}")
                    raise
                except Exception as e:
                    self.failed_count += 1
                    logging.error(f"Failed {conv_id}: {e}", exc_info=True)
                    self.storage.update_conversation_status(
                        conv_id, 'failed', error_message=str(e)
                    )
                    
        # Create all tasks with staggered start times
        tasks = []
        for i, (conv_id, conv_config) in enumerate(conversations):
            if self.daemon and self.daemon.is_stopping():
                break
            task = asyncio.create_task(run_with_semaphore(conv_id, conv_config))
            tasks.append(task)
            self.active_tasks[id(task)] = task
            
            # Add delay between task creation to avoid thundering herd
            # This helps prevent initial bursts of API calls
            if i < len(conversations) - 1:
                await asyncio.sleep(2.0)  # 2 second delay between starting conversations
            
        # Wait for all to complete or cancellation
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions that weren't already handled
            for i, result in enumerate(results):
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                    logging.error(f"Task {i} exception: {result}")
                    
        except asyncio.CancelledError:
            # Daemon is stopping, cancel all tasks
            logging.info("Cancelling all active tasks...")
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Wait for cancellations to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        finally:
            # Clean up task tracking
            self.active_tasks.clear()
            
        # Update experiment status
        final_status = 'completed'
        if self.daemon and self.daemon.is_stopping():
            final_status = 'failed'  # Use 'failed' instead of 'interrupted'
        elif self.failed_count > 0:
            final_status = 'failed'  # Use 'failed' instead of 'completed_with_errors'
            
        self.storage.update_experiment_status(experiment_id, final_status)
        
        logging.info(
            f"Experiment {experiment_id} {final_status}: "
            f"{self.completed_count} succeeded, {self.failed_count} failed"
        )
        
        return experiment_id
        
    def get_active_conversation_count(self) -> int:
        """Get number of currently active conversations."""
        return sum(1 for task in self.active_tasks.values() if not task.done())