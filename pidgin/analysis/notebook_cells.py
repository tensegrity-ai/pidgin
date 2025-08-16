"""Cell creation logic extracted from NotebookGenerator."""

from typing import Any, Dict, List, Optional

from ..io.logger import get_logger
from .cells import (
    ConvergenceCells,
    SetupCells,
    StatisticsCells,
    VisualizationCells,
    VocabularyCells,
)

logger = get_logger("notebook_cells")


class NotebookCells:
    """Handles creation of all notebook cells.

    This class delegates to specialized cell creators for different
    types of analysis, keeping the main class small and focused.
    """

    def __init__(self):
        """Initialize cell creators."""
        self.setup = SetupCells()
        self.statistics = StatisticsCells()
        self.convergence = ConvergenceCells()
        self.vocabulary = VocabularyCells()
        self.visualization = VisualizationCells()

    # Delegate to setup cells
    def format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp to readable format."""
        return self.setup.format_timestamp(timestamp)

    def create_title_cell(self, data: Dict[str, Any]):
        """Create title and overview markdown cell."""
        return self.setup.create_title_cell(data)

    def create_setup_cell(self):
        """Create setup and imports code cell."""
        return self.setup.create_setup_cell()

    def create_data_loading_cell(
        self,
        manifest_or_data: Dict[str, Any],
        turn_metrics_data: Optional[List[Dict]] = None,
        messages_data: Optional[List[Dict]] = None,
        conversations_data: Optional[List[Dict]] = None,
    ):
        """Create data loading code cell."""
        return self.setup.create_data_loading_cell(
            manifest_or_data, turn_metrics_data, messages_data, conversations_data
        )

    def create_export_cell(self):
        """Create data export code cell."""
        return self.setup.create_export_cell()

    # Delegate to statistics cells
    def create_statistics_cell(self):
        """Create basic statistics code cell."""
        return self.statistics.create_statistics_cell()

    def create_length_analysis_cell(self):
        """Create message length analysis code cell."""
        return self.statistics.create_length_analysis_cell()

    # Delegate to convergence cells
    def create_convergence_analysis_cell(self):
        """Create convergence analysis visualization code cell."""
        return self.convergence.create_convergence_analysis_cell()

    def create_advanced_metrics_markdown_cell(self):
        """Create advanced metrics explanation markdown cell."""
        return self.convergence.create_advanced_metrics_markdown_cell()

    def create_advanced_metrics_code_cell(self):
        """Create advanced metrics analysis code cell."""
        return self.convergence.create_advanced_metrics_code_cell()

    # Delegate to vocabulary cells
    def create_vocabulary_analysis_cell(self):
        """Create vocabulary overlap analysis code cell."""
        return self.vocabulary.create_vocabulary_analysis_cell()

    # Delegate to visualization cells
    def create_turn_visualization_cell(self):
        """Create turn-by-turn visualization code cell."""
        return self.visualization.create_turn_visualization_cell()
