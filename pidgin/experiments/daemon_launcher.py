"""Launch experiment daemon - called by subprocess."""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from . import ExperimentConfig
from .daemon import ExperimentDaemon
from .runner import ExperimentRunner


async def run_experiment(
    experiment_id: str,
    experiment_dir: str,
    config: ExperimentConfig,
    daemon: ExperimentDaemon,
):
    """Run the experiment with the experiment runner.

    Args:
        experiment_id: Existing experiment ID to use
        experiment_dir: Directory name to use for the experiment
        config: Experiment configuration
        daemon: Daemon instance
    """
    # Get the output directory using consistent logic
    from ..io.paths import get_experiments_dir

    output_dir = get_experiments_dir()

    # Ensure the output directory is absolute
    output_dir = output_dir.resolve()
    logging.info(f"Using output directory: {output_dir}")

    runner = ExperimentRunner(output_dir, daemon=daemon)

    try:
        await runner.run_experiment_with_id(experiment_id, experiment_dir, config)
    except asyncio.CancelledError:
        logging.info("Experiment cancelled")
        raise
    except Exception as e:
        logging.error(f"Experiment failed: {e}", exc_info=True)
        raise
    finally:
        pass


def main():
    """Main entry point for daemon launcher."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", required=True, help="Experiment ID")
    parser.add_argument(
        "--experiment-dir", required=True, help="Experiment directory name"
    )
    parser.add_argument("--config", required=True, help="JSON config")
    parser.add_argument(
        "--working-dir", required=True, help="Working directory for output"
    )
    args = parser.parse_args()

    # Parse config
    try:
        config_dict = json.loads(args.config)
        config = ExperimentConfig(**config_dict)
    except Exception as e:
        sys.stderr.write(f"Failed to parse config: {e}\n")
        sys.exit(1)

    # Set both the original CWD and project base for consistency
    working_dir = Path(args.working_dir)
    os.environ["PIDGIN_ORIGINAL_CWD"] = str(working_dir)
    os.environ["PIDGIN_PROJECT_BASE"] = str(working_dir)

    # Create daemon with absolute path based on working directory
    from ..io.directories import get_cache_dir

    active_dir = get_cache_dir() / "active_experiments"

    # Ensure directories exist before daemonizing
    try:
        active_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        sys.stderr.write(f"Error creating active directory: {e}\n")
        sys.exit(1)

    daemon = ExperimentDaemon(args.experiment_id, active_dir)

    # Set up logging first - put log file in experiment directory
    from ..io.paths import get_experiments_dir

    experiments_dir = get_experiments_dir()
    exp_dir = experiments_dir / args.experiment_dir
    log_file = exp_dir / "experiment.log"
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging to write to file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler(sys.stderr),  # Also log to stderr for startup
        ],
        force=True,  # Override any existing config
    )

    # Log environment info
    logging.info(f"Environment has {len(os.environ)} variables")
    logging.info(f"ANTHROPIC_API_KEY present: {'ANTHROPIC_API_KEY' in os.environ}")
    logging.info(f"OPENAI_API_KEY present: {'OPENAI_API_KEY' in os.environ}")
    logging.info(f"Working directory: {os.getcwd()}")

    # Set up the daemon
    try:
        daemon.setup()
    except Exception as e:
        logging.error(f"Failed to set up background process: {e}", exc_info=True)
        sys.exit(1)

    # Remove stderr handler after setup to only log to file
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
            root_logger.removeHandler(handler)

    try:
        logging.info(f"Starting experiment {args.experiment_id}")
        logging.info(f"Config: {config.name} - {config.repetitions} repetitions")
        logging.info(f"GOOGLE_API_KEY present: {'GOOGLE_API_KEY' in os.environ}")
        logging.info(f"XAI_API_KEY present: {'XAI_API_KEY' in os.environ}")
        logging.info(
            f"PIDGIN_ORIGINAL_CWD: {os.getenv('PIDGIN_ORIGINAL_CWD', 'Not set')}"
        )

        # Run experiment
        try:
            asyncio.run(
                run_experiment(args.experiment_id, args.experiment_dir, config, daemon)
            )
            logging.info("Experiment completed successfully")
        except KeyboardInterrupt:
            logging.info("Experiment interrupted by user")
        except asyncio.CancelledError:
            logging.info("Experiment cancelled")
        except Exception as e:
            logging.error(f"Experiment failed: {e}", exc_info=True)
            sys.exit(1)
    except Exception as e:
        # If we can't even set up logging, write to stderr
        sys.stderr.write(f"Fatal error in daemon: {e}\n")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        daemon.cleanup()
        logging.info("Daemon cleanup complete")


if __name__ == "__main__":
    main()
