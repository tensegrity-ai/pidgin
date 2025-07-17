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
    experiment_id: str, experiment_dir: str, config: ExperimentConfig, daemon: ExperimentDaemon
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

    runner = ExperimentRunner(output_dir, daemon)

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
    parser.add_argument("--experiment-dir", required=True, help="Experiment directory name")
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
    active_dir = working_dir / "pidgin_output" / "experiments" / "active"

    # Pre-startup logging (before logging is configured)
    print(f"[pidgin-daemon] Starting experiment {args.experiment_id}", file=sys.stderr)
    print(f"[pidgin-daemon] Working directory: {working_dir}", file=sys.stderr)
    print(f"[pidgin-daemon] Active directory: {active_dir}", file=sys.stderr)
    print(
        f"[pidgin-daemon] PID file: {active_dir / f'{args.experiment_id}.pid'}",
        file=sys.stderr,
    )

    # Ensure directories exist before daemonizing
    try:
        active_dir.mkdir(parents=True, exist_ok=True)
        print(
            f"[pidgin-daemon] Created active directory: {active_dir}", file=sys.stderr
        )
    except Exception as e:
        print(f"[pidgin-daemon] Error creating active directory: {e}", file=sys.stderr)
        sys.exit(1)

    daemon = ExperimentDaemon(args.experiment_id, active_dir)

    # Daemonize
    try:
        daemon.daemonize()
    except Exception as e:
        print(f"[pidgin-daemon] Failed to daemonize: {e}", file=sys.stderr)
        sys.exit(1)

    # Now we're in daemon process
    # Set up logging
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # Override any existing config
        )

        logging.info(f"Starting experiment {args.experiment_id}")
        logging.info(f"Config: {config.name} - {config.repetitions} repetitions")
        logging.info(
            f"PIDGIN_PROJECT_BASE after daemon: {os.environ.get('PIDGIN_PROJECT_BASE', 'NOT SET')}"
        )
        logging.info(f"Current working directory: {os.getcwd()}")

        # Run experiment
        try:
            asyncio.run(run_experiment(args.experiment_id, args.experiment_dir, config, daemon))
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
