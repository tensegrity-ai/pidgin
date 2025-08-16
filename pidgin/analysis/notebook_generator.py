"""Generate Jupyter notebooks for experiment analysis."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import nbformat
    from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

    NBFORMAT_AVAILABLE = True
except ImportError:
    NBFORMAT_AVAILABLE = False
    nbformat = None

from ..database.event_store import EventStore
from ..io.logger import get_logger
from .notebook_cells import NotebookCells

logger = get_logger("notebook_generator")


class NotebookGenerator:
    """Generates Jupyter notebooks for experiment analysis."""

    def __init__(
        self,
        experiment_dir: Path,
        event_store: EventStore,
        cells: Optional[NotebookCells] = None,
    ):
        """Initialize with experiment directory and EventStore.

        Args:
            experiment_dir: Path to experiment directory
            event_store: EventStore instance for database access
            cells: Optional custom cells instance
        """
        self.experiment_dir = experiment_dir
        self.manifest_path = experiment_dir / "manifest.json"
        self.notebook_path = experiment_dir / "analysis.ipynb"
        self.event_store = event_store
        self.cells = cells or NotebookCells()

    def generate(self) -> bool:
        """Generate analysis notebook from experiment data.

        Returns:
            True if successful, False otherwise
        """
        if not NBFORMAT_AVAILABLE:
            logger.debug("Jupyter notebook generation skipped (nbformat not installed)")
            # Don't log the install instruction - this is handled in the runner
            return False

        try:
            if not self.manifest_path.exists():
                logger.warning(f"No manifest.json found in {self.experiment_dir}")
                return False

            with open(self.manifest_path) as f:
                manifest = json.load(f)

            # Create notebook
            nb = self._create_notebook(manifest)

            # Write notebook
            with open(self.notebook_path, "w") as f:
                nbformat.write(nb, f)

            logger.debug(
                f"Generated analysis.ipynb for experiment {manifest.get('name', 'unknown')}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to generate notebook: {e}")
            return False

    def _create_notebook(
        self, manifest: Dict[str, Any]
    ) -> Optional["nbformat.NotebookNode"]:
        """Create notebook structure from manifest data.

        Args:
            manifest: Experiment manifest data

        Returns:
            Jupyter notebook object
        """
        # Load experiment data
        experiment_id = manifest.get("experiment_id")
        if not experiment_id:
            logger.error("No experiment_id in manifest")
            return None

        # Get experiment data from EventStore
        experiment_data = self.event_store.get_experiment(experiment_id)
        if not experiment_data:
            logger.error(f"Experiment {experiment_id} not found in database")
            return None

        # Get conversations data
        conversations = self.event_store.get_experiment_conversations(experiment_id)

        # Get metrics for all conversations
        all_metrics = []
        for conv in conversations:
            metrics = self.event_store.get_conversation_turn_metrics(
                conv["conversation_id"]
            )
            all_metrics.extend(metrics)

        # Prepare data dictionary
        data = {
            "manifest": manifest,
            "experiment": experiment_data,
            "conversations": conversations,
            "metrics": all_metrics,
        }

        cells = []

        # Title and overview
        cells.append(self.cells.create_title_cell(data))

        # Setup and imports
        cells.append(self.cells.create_setup_cell())

        # Load experiment data
        cells.append(self.cells.create_data_loading_cell(data))

        # Basic statistics
        cells.append(self.cells.create_statistics_cell())

        # Convergence analysis
        cells.append(self.cells.create_convergence_analysis_cell())

        # Message length analysis
        cells.append(self.cells.create_length_analysis_cell())

        # Vocabulary analysis
        cells.append(self.cells.create_vocabulary_analysis_cell())

        # Advanced metrics information
        cells.append(self.cells.create_advanced_metrics_markdown_cell())
        cells.append(self.cells.create_advanced_metrics_code_cell())

        # Turn-by-turn visualization
        cells.append(self.cells.create_turn_visualization_cell())

        # Export options
        cells.append(self.cells.create_export_cell())

        # Create notebook
        nb = new_notebook()
        nb.cells = cells
        nb.metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        }

        return nb
