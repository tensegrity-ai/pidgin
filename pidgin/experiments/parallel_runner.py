"""Parallel experiment runner with rate limiting."""

import asyncio
import logging
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict

from .runner import ExperimentRunner
from .config import ExperimentConfig
from .storage import ExperimentStore
from .daemon import ExperimentDaemon
from ..config.models import get_model_config


class ParallelExperimentRunner(ExperimentRunner):
    """Runs experiments with parallel conversation execution."""
    
    # Provider rate limits (requests per minute)
    # Conservative defaults to avoid rate limiting
    RATE_LIMITS = {
        "anthropic": 50,  # Anthropic allows ~50-60 rpm
        "openai": 60,     # OpenAI allows ~60 rpm for GPT-4
        "google": 60,     # Google allows ~60 rpm
        "xai": 50,        # xAI estimate
    }
    
    # Conversations per minute we'll actually attempt
    # More conservative to account for conversation duration
    SAFE_RATES = {
        "anthropic": 5,
        "openai": 8,
        "google": 5,
        "xai": 5,
    }
    
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
        """Calculate safe parallelism level based on providers.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Maximum number of parallel conversations
        """
        # Determine which providers are in use
        providers = set()
        
        # Get provider for each model
        provider_a = self._get_provider_type(config.agent_a_model)
        provider_b = self._get_provider_type(config.agent_b_model)
        
        providers.add(provider_a)
        providers.add(provider_b)
        
        # Remove unknown providers
        providers.discard('unknown')
        
        if not providers:
            logging.warning("Unknown providers, using conservative parallelism")
            return 2
            
        # If using multiple different providers, we can be more aggressive
        if len(providers) > 1:
            # Sum the limits of used providers
            total_limit = sum(self.SAFE_RATES.get(p, 3) for p in providers)
            return min(total_limit, 10)  # Cap at 10 for safety
            
        # Single provider - use its limit
        provider = providers.pop()
        return self.SAFE_RATES.get(provider, 3)
        
    def _get_provider_type(self, model: str) -> str:
        """Determine provider from model name.
        
        Args:
            model: Model name or alias
            
        Returns:
            Provider type string
        """
        config = get_model_config(model)
        if config:
            return config.provider
            
        # Fallback pattern matching
        model_lower = model.lower()
        if 'claude' in model_lower or model in ['opus', 'sonnet', 'haiku']:
            return 'anthropic'
        elif model_lower.startswith('gpt') or model_lower.startswith('o'):
            return 'openai'
        elif 'gemini' in model_lower:
            return 'google'
        elif 'grok' in model_lower:
            return 'xai'
        else:
            return 'unknown'
            
    async def run_experiment(self, config: ExperimentConfig) -> str:
        """Run experiment with parallel execution.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Experiment ID
        """
        experiment_id = self.storage.create_experiment(config.name, config.dict())
        self.storage.update_experiment_status(experiment_id, 'running')
        
        # Calculate parallelism
        max_parallel = config.max_parallel or self.calculate_parallelism(config)
        logging.info(f"Starting experiment {experiment_id} with parallelism: {max_parallel}")
        
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
                    
        # Create all tasks
        tasks = []
        for conv_id, conv_config in conversations:
            if self.daemon and self.daemon.is_stopping():
                break
            task = asyncio.create_task(run_with_semaphore(conv_id, conv_config))
            tasks.append(task)
            self.active_tasks[id(task)] = task
            
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