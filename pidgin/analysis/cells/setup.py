"""Setup and data loading cells for notebooks."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .base import CellBase

if TYPE_CHECKING:
    try:
        from nbformat import NotebookNode
    except ImportError:
        NotebookNode = Dict[str, Any]


class SetupCells(CellBase):
    """Creates setup, title, and data loading cells."""

    def format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp to readable format."""
        if not timestamp:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, AttributeError):
            return timestamp

    def create_title_cell(self, data: Dict[str, Any]) -> "NotebookNode":
        """Create title and overview markdown cell.

        Args:
            data: Data dictionary containing manifest and other experiment data

        Returns:
            Jupyter notebook markdown cell
        """
        # Handle both old style (direct manifest) and new style (data dict)
        if "manifest" in data:
            manifest = data["manifest"]
        else:
            manifest = data

        exp_name = manifest.get("name", "Unknown Experiment")
        exp_id = manifest.get("experiment_id", "unknown")
        created_at = manifest.get("created_at", "")

        content = f"""# Experiment Analysis: {exp_name}

**Experiment ID**: `{exp_id}`
**Created**: {self.format_timestamp(created_at)}
**Status**: {manifest.get("status", "unknown")}

## Configuration
- **Agent A**: {manifest.get("configuration", {}).get("model_a", "unknown")}
- **Agent B**: {manifest.get("configuration", {}).get("model_b", "unknown")}
- **Max Turns**: {manifest.get("configuration", {}).get("max_turns", 0)}
- **Conversations**: {manifest.get("total_conversations", 0)}

This notebook provides automated analysis of the experiment results."""

        return self._make_markdown_cell(content)

    def create_setup_cell(self) -> "NotebookNode":
        """Create setup and imports code cell.

        Returns:
            Jupyter notebook code cell
        """
        code = """# Import required libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path

# Set up plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Configure display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
pd.set_option('display.float_format', '{:.3f}'.format)

# Define experiment directory
exp_dir = Path(".")
print(f"Analyzing experiment in: {exp_dir.resolve()}")"""

        return self._make_code_cell(code)

    def create_data_loading_cell(
        self,
        manifest_or_data: Dict[str, Any],
        turn_metrics_data: Optional[List[Dict]] = None,
        messages_data: Optional[List[Dict]] = None,
        conversations_data: Optional[List[Dict]] = None,
    ) -> "NotebookNode":
        """Create data loading code cell.

        Args:
            manifest_or_data: Either manifest dict (old style) or data dict with manifest key (new style)
            turn_metrics_data: Turn metrics from database (old style, optional)
            messages_data: Messages from database (old style, optional)
            conversations_data: Conversations from database (old style, optional)

        Returns:
            Jupyter notebook code cell
        """
        # Handle both old style (separate args) and new style (data dict)
        if (
            turn_metrics_data is not None
            or messages_data is not None
            or conversations_data is not None
        ):
            # Old style - first arg is manifest, other args are data
            manifest = manifest_or_data
            turn_metrics_data = turn_metrics_data or []
            messages_data = messages_data or []
            conversations_data = conversations_data or []
        elif "manifest" in manifest_or_data:
            # New style - data dict
            manifest = manifest_or_data["manifest"]
            turn_metrics_data = manifest_or_data.get("metrics", [])
            messages_data = []  # Not provided in new style
            conversations_data = manifest_or_data.get("conversations", [])
        else:
            # Old style with only manifest
            manifest = manifest_or_data
            turn_metrics_data = []
            messages_data = []
            conversations_data = []

        exp_id = manifest.get("experiment_id", "unknown")

        code = f"""# Load experiment data from EventStore
experiment_id = "{exp_id}"

# Data loaded from EventStore at notebook generation time
turn_metrics_data = {turn_metrics_data}
messages_data = {messages_data}
conversations_data = {conversations_data}

# Convert to DataFrames
turn_metrics = pd.DataFrame(turn_metrics_data)
messages = pd.DataFrame(messages_data)
conversations = pd.DataFrame(conversations_data)

print(f"Loaded {{len(turn_metrics)}} turn metrics from {{len(conversations)}} conversations")

# Display basic info about the loaded data
if not turn_metrics.empty:
    print("Turn metrics columns:", list(turn_metrics.columns))
if not messages.empty:
    print("Messages columns:", list(messages.columns))
if not conversations.empty:
    print("Conversations columns:", list(conversations.columns))"""

        return self._make_code_cell(code)

    def create_export_cell(self) -> "NotebookNode":
        """Create data export code cell.

        Returns:
            Jupyter notebook code cell
        """
        code = """# Export processed data for further analysis
output_dir = Path("analysis_output")
output_dir.mkdir(exist_ok=True)

# Export metrics
if not turn_metrics.empty:
    turn_metrics.to_csv(output_dir / "turn_metrics.csv", index=False)
    print(f"Exported turn metrics to {output_dir / 'turn_metrics.csv'}")

# Export summary statistics
summary_stats = {
    'total_conversations': len(conversations),
    'total_turns': len(turn_metrics),
    'avg_turns_per_conversation': len(turn_metrics) / len(conversations) if len(conversations) > 0 else 0,
}

if not turn_metrics.empty and 'convergence_score' in turn_metrics.columns:
    summary_stats.update({
        'mean_convergence': turn_metrics['convergence_score'].mean(),
        'final_convergence': turn_metrics.groupby('conversation_id')['convergence_score'].last().mean(),
    })

with open(output_dir / "summary_stats.json", "w") as f:
    json.dump(summary_stats, f, indent=2)
    print(f"Exported summary statistics to {output_dir / 'summary_stats.json'}")"""

        return self._make_code_cell(code)
