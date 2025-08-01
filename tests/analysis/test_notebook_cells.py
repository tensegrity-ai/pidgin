"""Tests for NotebookCells class extracted from NotebookGenerator."""

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Mock nbformat if not available
try:
    import nbformat
    from nbformat.v4 import new_code_cell, new_markdown_cell
    NBFORMAT_AVAILABLE = True
except ImportError:
    NBFORMAT_AVAILABLE = False
    nbformat = MagicMock()
    new_code_cell = MagicMock()
    new_markdown_cell = MagicMock()

from pidgin.analysis.notebook_cells import NotebookCells


class TestNotebookCells:
    """Test suite for NotebookCells."""

    @pytest.fixture
    def cells_creator(self):
        """Create a NotebookCells instance."""
        return NotebookCells()

    @pytest.fixture
    def sample_manifest(self):
        """Create sample manifest data."""
        return {
            "name": "Test Experiment",
            "experiment_id": "exp123",
            "created_at": "2024-01-01T10:00:00Z",
            "status": "completed",
            "total_conversations": 5,
            "configuration": {
                "model_a": "gpt-4",
                "model_b": "claude-3",
                "max_turns": 25,
            },
        }

    @pytest.fixture
    def sample_metrics_data(self):
        """Create sample metrics data."""
        return {
            "turn_metrics": [
                {
                    "conversation_id": "conv1",
                    "turn_number": 1,
                    "convergence_score": 0.2,
                    "vocabulary_overlap": 0.1,
                    "structural_similarity": 0.15,
                    "agent_a_message_length": 50,
                    "agent_b_message_length": 45,
                },
                {
                    "conversation_id": "conv1",
                    "turn_number": 2,
                    "convergence_score": 0.3,
                    "vocabulary_overlap": 0.2,
                    "structural_similarity": 0.25,
                    "agent_a_message_length": 60,
                    "agent_b_message_length": 55,
                },
            ],
            "messages": [
                {
                    "conversation_id": "conv1",
                    "turn_number": 1,
                    "role": "agent_a",
                    "content": "Hello",
                },
                {
                    "conversation_id": "conv1",
                    "turn_number": 1,
                    "role": "agent_b",
                    "content": "Hi there",
                },
            ],
            "conversations": [
                {
                    "conversation_id": "conv1",
                    "status": "completed",
                },
            ],
        }

    def test_create_title_cell(self, cells_creator, sample_manifest):
        """Test title cell creation."""
        cell = cells_creator.create_title_cell(sample_manifest)

        if NBFORMAT_AVAILABLE:
            assert hasattr(cell, "source")
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Experiment Analysis: Test Experiment" in content
        assert "**Experiment ID**: `exp123`" in content
        assert "**Status**: completed" in content
        assert "**Agent A**: gpt-4" in content
        assert "**Agent B**: claude-3" in content

    def test_create_setup_cell(self, cells_creator):
        """Test setup cell creation."""
        cell = cells_creator.create_setup_cell()

        if NBFORMAT_AVAILABLE:
            assert hasattr(cell, "source")
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "import pandas as pd" in content
        assert "import matplotlib.pyplot as plt" in content
        assert "import seaborn as sns" in content
        assert "plt.style.use('seaborn-v0_8-darkgrid')" in content

    def test_create_data_loading_cell(self, cells_creator, sample_manifest, sample_metrics_data):
        """Test data loading cell creation."""
        cell = cells_creator.create_data_loading_cell(
            sample_manifest,
            sample_metrics_data["turn_metrics"],
            sample_metrics_data["messages"],
            sample_metrics_data["conversations"],
        )

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert 'experiment_id = "exp123"' in content
        assert "turn_metrics_data = [" in content
        assert "messages_data = [" in content
        assert "conversations_data = [" in content
        assert "turn_metrics = pd.DataFrame(turn_metrics_data)" in content

    def test_create_statistics_cell(self, cells_creator):
        """Test statistics cell creation."""
        cell = cells_creator.create_statistics_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Basic Statistics" in content
        assert "Total conversations:" in content
        assert "Average turns per conversation:" in content
        assert "Average convergence score:" in content

    def test_create_convergence_analysis_cell(self, cells_creator):
        """Test convergence analysis cell creation."""
        cell = cells_creator.create_convergence_analysis_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Convergence Analysis" in content
        assert "fig, axes = plt.subplots(2, 2, figsize=(15, 10))" in content
        assert "Convergence Trajectories" in content
        assert "Average Convergence Across All Conversations" in content

    def test_create_length_analysis_cell(self, cells_creator):
        """Test message length analysis cell creation."""
        cell = cells_creator.create_length_analysis_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Message Length Analysis" in content
        assert "Message Length Distribution by Agent" in content
        assert "Message Length Convergence Over Time" in content

    def test_create_vocabulary_analysis_cell(self, cells_creator):
        """Test vocabulary analysis cell creation."""
        cell = cells_creator.create_vocabulary_analysis_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Vocabulary Analysis" in content
        assert "Vocabulary Growth Over Turns" in content
        assert "vocabulary_overlap" in content

    def test_create_advanced_metrics_markdown_cell(self, cells_creator):
        """Test advanced metrics markdown cell creation."""
        cell = cells_creator.create_advanced_metrics_markdown_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "## Advanced Metrics (Post-Processing)" in content
        assert "semantic_similarity" in content
        assert "sentiment_convergence" in content
        assert "These metrics are intentionally not calculated by Pidgin" in content

    def test_create_advanced_metrics_code_cell(self, cells_creator):
        """Test advanced metrics code example cell creation."""
        cell = cells_creator.create_advanced_metrics_code_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Example: Calculate semantic similarity" in content
        assert "sentence-transformers" in content
        assert "# Uncomment to run:" in content

    def test_create_turn_visualization_cell(self, cells_creator):
        """Test turn-by-turn visualization cell creation."""
        cell = cells_creator.create_turn_visualization_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Turn-by-Turn Metrics Visualization" in content
        assert "sample_conv_id" in content
        assert "metrics_to_plot" in content

    def test_create_export_cell(self, cells_creator):
        """Test export cell creation."""
        cell = cells_creator.create_export_cell()

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "# Export Options" in content
        assert "conv_summary.to_csv('conversation_summary.csv')" in content
        assert "=== Experiment Report ===" in content

    def test_format_timestamp(self, cells_creator):
        """Test timestamp formatting."""
        # Test with valid ISO timestamp
        result = cells_creator.format_timestamp("2024-01-01T10:00:00Z")
        assert result == "2024-01-01 10:00:00 UTC"

        # Test with empty string
        result = cells_creator.format_timestamp("")
        assert result == "Unknown"

        # Test with invalid timestamp
        result = cells_creator.format_timestamp("invalid")
        assert result == "invalid"

        # Test with None
        result = cells_creator.format_timestamp(None)
        assert result == "Unknown"

    def test_create_data_loading_cell_empty_data(self, cells_creator, sample_manifest):
        """Test data loading cell with empty data."""
        cell = cells_creator.create_data_loading_cell(
            sample_manifest,
            turn_metrics_data=[],
            messages_data=[],
            conversations_data=[],
        )

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "turn_metrics_data = []" in content
        assert "messages_data = []" in content
        assert "conversations_data = []" in content

    def test_create_title_cell_missing_config(self, cells_creator):
        """Test title cell with missing configuration."""
        manifest = {
            "name": "Test",
            "experiment_id": "exp123",
            "created_at": "",
            "status": "unknown",
            "total_conversations": 0,
            "configuration": {},  # Empty config
        }

        cell = cells_creator.create_title_cell(manifest)

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        assert "**Agent A**: unknown" in content
        assert "**Agent B**: unknown" in content
        assert "**Max Turns**: 0" in content

    def test_all_cells_have_correct_types(self, cells_creator, sample_manifest, sample_metrics_data):
        """Test that all cell creation methods return the correct type."""
        if not NBFORMAT_AVAILABLE:
            pytest.skip("nbformat not available")

        # Test markdown cells
        markdown_cells = [
            cells_creator.create_title_cell(sample_manifest),
            cells_creator.create_advanced_metrics_markdown_cell(),
        ]

        for cell in markdown_cells:
            assert cell.cell_type == "markdown"

        # Test code cells
        code_cells = [
            cells_creator.create_setup_cell(),
            cells_creator.create_statistics_cell(),
            cells_creator.create_convergence_analysis_cell(),
            cells_creator.create_length_analysis_cell(),
            cells_creator.create_vocabulary_analysis_cell(),
            cells_creator.create_advanced_metrics_code_cell(),
            cells_creator.create_turn_visualization_cell(),
            cells_creator.create_export_cell(),
        ]

        for cell in code_cells:
            assert cell.cell_type == "code"

    def test_data_loading_preserves_structure(self, cells_creator, sample_manifest, sample_metrics_data):
        """Test that data loading cell preserves the structure of input data."""
        cell = cells_creator.create_data_loading_cell(
            sample_manifest,
            sample_metrics_data["turn_metrics"],
            sample_metrics_data["messages"],
            sample_metrics_data["conversations"],
        )

        if NBFORMAT_AVAILABLE:
            content = cell.source
        else:
            # When nbformat is not available, we get a dict
            content = cell["source"]

        # Verify the data is properly serialized
        assert "'conversation_id': 'conv1'" in content
        assert "'turn_number': 1" in content
        assert "'convergence_score': 0.2" in content