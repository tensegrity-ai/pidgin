"""Launch experiment daemon - called by subprocess."""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path

from . import ExperimentConfig, ExperimentStore
from .daemon import ExperimentDaemon
from .parallel_runner import ParallelExperimentRunner


async def run_experiment(config: ExperimentConfig, daemon: ExperimentDaemon):
    """Run the experiment with the parallel runner.
    
    Args:
        config: Experiment configuration
        daemon: Daemon instance
    """
    storage = ExperimentStore()
    runner = ParallelExperimentRunner(storage, daemon)
    
    try:
        await runner.run_experiment(config)
    except asyncio.CancelledError:
        logging.info("Experiment cancelled")
        raise
    except Exception as e:
        logging.error(f"Experiment failed: {e}", exc_info=True)
        raise


def main():
    """Main entry point for daemon launcher."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment-id', required=True, help='Experiment ID')
    parser.add_argument('--config', required=True, help='JSON config')
    args = parser.parse_args()
    
    # Parse config
    try:
        config_dict = json.loads(args.config)
        config = ExperimentConfig(**config_dict)
    except Exception as e:
        sys.stderr.write(f"Failed to parse config: {e}\n")
        sys.exit(1)
    
    # Set project base path as environment variable before daemonizing
    # This will be preserved across the fork
    project_base = Path(".").resolve()
    os.environ['PIDGIN_PROJECT_BASE'] = str(project_base)
    
    # Create daemon with absolute path
    daemon = ExperimentDaemon(
        args.experiment_id,
        Path("./pidgin_output/experiments/active").resolve()
    )
    
    # Daemonize
    daemon.daemonize()
    
    # Now we're in daemon process
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Override any existing config
    )
    
    logging.info(f"Starting experiment {args.experiment_id}")
    logging.info(f"Config: {config.name} - {config.repetitions} repetitions")
    
    # Run experiment
    try:
        asyncio.run(run_experiment(config, daemon))
        logging.info("Experiment completed successfully")
    except KeyboardInterrupt:
        logging.info("Experiment interrupted by user")
    except asyncio.CancelledError:
        logging.info("Experiment cancelled")
    except Exception as e:
        logging.error(f"Experiment failed: {e}", exc_info=True)
    finally:
        daemon.cleanup()
        logging.info("Daemon cleanup complete")


if __name__ == '__main__':
    main()