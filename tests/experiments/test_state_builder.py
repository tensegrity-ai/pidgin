"""Tests for StateBuilder class."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pidgin.experiments.state_builder import StateBuilder, get_state_builder
from pidgin.experiments.state_types import ExperimentState


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_manifest():
    """Create a sample manifest.json content."""
    return {
        "experiment_id": "test_exp_123",
        "name": "Test Experiment",
        "status": "running",
        "total_conversations": 3,
        "completed_conversations": 2,
        "failed_conversations": 1,
        "created_at": "2023-01-01T10:00:00Z",
        "started_at": "2023-01-01T10:05:00Z",
        "completed_at": None,
        "config": {
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "max_turns": 10,
        },
        "conversations": {
            "conv_1": {
                "status": "completed",
                "turns_completed": 5,
                "last_updated": "2023-01-01T10:15:00Z",
            },
            "conv_2": {
                "status": "running",
                "turns_completed": 3,
                "last_updated": "2023-01-01T10:20:00Z",
            },
        },
    }


@pytest.fixture
def sample_legacy_metadata():
    """Create a sample metadata.json content for legacy format."""
    return {
        "experiment_id": "legacy_exp_456",
        "name": "Legacy Experiment",
        "status": "completed",
        "total_conversations": 2,
        "completed_conversations": 2,
        "failed_conversations": 0,
        "started_at": "2023-01-01T09:00:00Z",
        "completed_at": "2023-01-01T09:30:00Z",
    }


@pytest.fixture
def sample_jsonl_events():
    """Create sample JSONL events for testing."""
    return [
        {
            "event_type": "ConversationStartEvent",
            "conversation_id": "conv_1",
            "timestamp": "2023-01-01T10:10:00Z",
            "agent_a_model": "gpt-4",
            "agent_b_model": "claude-3",
            "initial_prompt": "Hello world",
        },
        {
            "event_type": "TurnCompleteEvent",
            "conversation_id": "conv_1",
            "turn_number": 1,
            "convergence_score": 0.25,
            "timestamp": "2023-01-01T10:12:00Z",
        },
        {
            "event_type": "TurnCompleteEvent",
            "conversation_id": "conv_1",
            "turn_number": 2,
            "convergence_score": 0.75,
            "timestamp": "2023-01-01T10:14:00Z",
        },
        {
            "event_type": "ContextTruncationEvent",
            "conversation_id": "conv_1",
            "turn_number": 3,
            "timestamp": "2023-01-01T10:13:00Z",
        },
        {
            "event_type": "ConversationEndEvent",
            "conversation_id": "conv_1",
            "timestamp": "2023-01-01T10:15:00Z",
        },
    ]


class TestStateBuilder:
    """Test StateBuilder functionality."""

    def test_init(self):
        """Test StateBuilder initialization."""
        builder = StateBuilder()
        assert builder.cache == {}

    def test_clear_cache(self):
        """Test cache clearing."""
        builder = StateBuilder()
        builder.cache[Path("/test")] = (123.0, Mock())

        builder.clear_cache()
        assert builder.cache == {}

    def test_get_experiment_state_no_manifest(self, temp_dir):
        """Test get_experiment_state when manifest doesn't exist."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        with patch.object(builder, "_get_legacy_state") as mock_legacy:
            mock_legacy.return_value = None

            result = builder.get_experiment_state(exp_dir)

            assert result is None
            mock_legacy.assert_called_once_with(exp_dir)

    def test_get_experiment_state_with_manifest(self, temp_dir, sample_manifest):
        """Test get_experiment_state with valid manifest."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        # Create manifest file
        manifest_path = exp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(sample_manifest, f)

        with patch.object(builder, "_build_from_manifest") as mock_build:
            mock_state = Mock(spec=ExperimentState)
            mock_build.return_value = mock_state

            result = builder.get_experiment_state(exp_dir)

            assert result == mock_state
            mock_build.assert_called_once_with(exp_dir, manifest_path)
            # Check that state was cached
            assert exp_dir in builder.cache

    def test_get_experiment_state_cached(self, temp_dir, sample_manifest):
        """Test get_experiment_state returns cached result."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        # Create manifest file
        manifest_path = exp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(sample_manifest, f)

        # Add to cache
        cached_state = Mock(spec=ExperimentState)
        mtime = manifest_path.stat().st_mtime
        builder.cache[exp_dir] = (mtime, cached_state)

        with patch.object(builder, "_build_from_manifest") as mock_build:
            result = builder.get_experiment_state(exp_dir)

            assert result == cached_state
            mock_build.assert_not_called()

    def test_list_experiments_empty_dir(self, temp_dir):
        """Test list_experiments with empty directory."""
        builder = StateBuilder()
        result = builder.list_experiments(temp_dir)
        assert result == []

    def test_list_experiments_with_experiments(self, temp_dir, sample_manifest):
        """Test list_experiments with valid experiments."""
        builder = StateBuilder()

        # Create experiment directories
        exp1_dir = temp_dir / "exp_test1"
        exp1_dir.mkdir()
        exp2_dir = temp_dir / "experiment_test2"
        exp2_dir.mkdir()

        # Create manifest files
        for exp_dir in [exp1_dir, exp2_dir]:
            manifest_path = exp_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(sample_manifest, f)

        # Mock the state building to return different states
        mock_state1 = Mock(spec=ExperimentState)
        mock_state1.status = "running"
        mock_state2 = Mock(spec=ExperimentState)
        mock_state2.status = "completed"

        with patch.object(
            builder, "get_experiment_state", side_effect=[mock_state1, mock_state2]
        ):
            result = builder.list_experiments(temp_dir)

            assert len(result) == 2
            assert mock_state1 in result
            assert mock_state2 in result

    def test_list_experiments_with_status_filter(self, temp_dir, sample_manifest):
        """Test list_experiments with status filtering."""
        builder = StateBuilder()

        # Create experiment directory
        exp_dir = temp_dir / "exp_test"
        exp_dir.mkdir()
        manifest_path = exp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(sample_manifest, f)

        # Mock state with running status
        mock_state = Mock(spec=ExperimentState)
        mock_state.status = "running"

        with patch.object(builder, "get_experiment_state", return_value=mock_state):
            # Test with matching filter
            result = builder.list_experiments(temp_dir, status_filter=["running"])
            assert len(result) == 1
            assert result[0] == mock_state

            # Test with non-matching filter
            result = builder.list_experiments(temp_dir, status_filter=["completed"])
            assert len(result) == 0

    def test_list_experiments_skips_files(self, temp_dir):
        """Test list_experiments skips non-directory files."""
        builder = StateBuilder()

        # Create a file that matches the pattern
        (temp_dir / "exp_test.txt").write_text("not a directory")

        result = builder.list_experiments(temp_dir)
        assert result == []

    def test_build_from_manifest_success(self, temp_dir, sample_manifest):
        """Test _build_from_manifest with valid manifest."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        manifest_path = exp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(sample_manifest, f)

        # Mock the JSONL reading methods
        with patch.object(
            builder, "_get_conversation_timestamps", return_value={}
        ), patch.object(
            builder, "_get_last_convergence", return_value=0.5
        ), patch.object(
            builder, "_get_truncation_info", return_value={"count": 1, "last_turn": 2}
        ):

            result = builder._build_from_manifest(exp_dir, manifest_path)

            assert result is not None
            assert result.experiment_id == "test_exp_123"
            assert result.name == "Test Experiment"
            assert result.status == "running"
            assert result.total_conversations == 3
            assert result.completed_conversations == 2
            assert result.failed_conversations == 1

            # Check conversations
            assert len(result.conversations) == 2
            assert "conv_1" in result.conversations
            assert "conv_2" in result.conversations

            conv1 = result.conversations["conv_1"]
            assert conv1.status == "completed"
            assert conv1.current_turn == 5
            assert conv1.max_turns == 10
            assert conv1.agent_a_model == "gpt-4"
            assert conv1.agent_b_model == "claude-3"
            assert conv1.last_convergence == 0.5
            assert conv1.truncation_count == 1
            assert conv1.last_truncation_turn == 2

    def test_build_from_manifest_file_error(self, temp_dir):
        """Test _build_from_manifest handles file read errors."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        manifest_path = exp_dir / "manifest.json"

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = builder._build_from_manifest(exp_dir, manifest_path)
            assert result is None

    def test_build_from_manifest_invalid_json(self, temp_dir):
        """Test _build_from_manifest handles invalid JSON."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        manifest_path = exp_dir / "manifest.json"
        manifest_path.write_text("invalid json content")

        result = builder._build_from_manifest(exp_dir, manifest_path)
        assert result is None

    def test_get_legacy_state_success(self, temp_dir, sample_legacy_metadata):
        """Test _get_legacy_state with valid metadata."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        metadata_path = exp_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(sample_legacy_metadata, f)

        result = builder._get_legacy_state(exp_dir)

        assert result is not None
        assert result.experiment_id == "legacy_exp_456"
        assert result.name == "Legacy Experiment"
        assert result.status == "completed"
        assert result.total_conversations == 2
        assert result.completed_conversations == 2
        assert result.failed_conversations == 0

        # Check timestamps
        assert result.started_at is not None
        assert result.completed_at is not None

    def test_get_legacy_state_no_file(self, temp_dir):
        """Test _get_legacy_state when metadata file doesn't exist."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        result = builder._get_legacy_state(exp_dir)
        assert result is None

    def test_get_legacy_state_invalid_json(self, temp_dir):
        """Test _get_legacy_state handles invalid JSON."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        metadata_path = exp_dir / "metadata.json"
        metadata_path.write_text("invalid json")

        result = builder._get_legacy_state(exp_dir)
        assert result is None

    def test_parse_timestamp_with_z_suffix(self):
        """Test _parse_timestamp with Z suffix."""
        builder = StateBuilder()
        timestamp_str = "2023-01-01T10:00:00Z"

        result = builder._parse_timestamp(timestamp_str)

        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 10
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == timezone.utc

    def test_parse_timestamp_with_timezone(self):
        """Test _parse_timestamp with timezone offset."""
        builder = StateBuilder()
        timestamp_str = "2023-01-01T10:00:00+05:00"

        result = builder._parse_timestamp(timestamp_str)

        assert result.year == 2023
        assert result.tzinfo is not None

    def test_parse_timestamp_naive(self):
        """Test _parse_timestamp with naive datetime."""
        builder = StateBuilder()
        timestamp_str = "2023-01-01T10:00:00"

        result = builder._parse_timestamp(timestamp_str)

        assert result.year == 2023
        assert result.tzinfo == timezone.utc

    def test_parse_timestamp_invalid_format(self):
        """Test _parse_timestamp with invalid format."""
        builder = StateBuilder()
        timestamp_str = "invalid-timestamp"

        result = builder._parse_timestamp(timestamp_str)

        # Should return current time as fallback
        assert result.tzinfo == timezone.utc
        assert abs((datetime.now(timezone.utc) - result).total_seconds()) < 1

    def test_get_last_convergence_no_files(self, temp_dir):
        """Test _get_last_convergence with no JSONL files."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        result = builder._get_last_convergence(exp_dir, "conv_1")
        assert result is None

    def test_get_last_convergence_with_events(self, temp_dir, sample_jsonl_events):
        """Test _get_last_convergence with valid JSONL events."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        # Create JSONL file
        jsonl_path = exp_dir / "conv_1.jsonl"
        with open(jsonl_path, "w") as f:
            for event in sample_jsonl_events:
                f.write(json.dumps(event) + "\n")

        result = builder._get_last_convergence(exp_dir, "conv_1")

        # Should return the last convergence score (0.75)
        assert result == 0.75

    def test_get_last_convergence_io_error(self, temp_dir):
        """Test _get_last_convergence handles IO errors."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        # Create JSONL file
        jsonl_path = exp_dir / "conv_1.jsonl"
        jsonl_path.write_text("some content")

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = builder._get_last_convergence(exp_dir, "conv_1")
            assert result is None

    def test_get_conversation_timestamps_success(self, temp_dir, sample_jsonl_events):
        """Test _get_conversation_timestamps with valid events."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        # Create JSONL file
        jsonl_path = exp_dir / "conv_1.jsonl"
        with open(jsonl_path, "w") as f:
            for event in sample_jsonl_events:
                f.write(json.dumps(event) + "\n")

        result = builder._get_conversation_timestamps(exp_dir, "conv_1")

        assert "started_at" in result
        assert "completed_at" in result
        assert result["started_at"] is not None
        assert result["completed_at"] is not None

    def test_get_conversation_timestamps_no_files(self, temp_dir):
        """Test _get_conversation_timestamps with no JSONL files."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        result = builder._get_conversation_timestamps(exp_dir, "conv_1")
        assert result == {}

    def test_get_truncation_info_success(self, temp_dir, sample_jsonl_events):
        """Test _get_truncation_info with valid events."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        # Create JSONL file
        jsonl_path = exp_dir / "conv_1.jsonl"
        with open(jsonl_path, "w") as f:
            for event in sample_jsonl_events:
                f.write(json.dumps(event) + "\n")

        result = builder._get_truncation_info(exp_dir, "conv_1")

        assert result["count"] == 1
        assert result["last_turn"] == 3

    def test_get_truncation_info_no_files(self, temp_dir):
        """Test _get_truncation_info with no JSONL files."""
        builder = StateBuilder()
        exp_dir = temp_dir / "test_exp"
        exp_dir.mkdir()

        result = builder._get_truncation_info(exp_dir, "conv_1")
        assert result == {}


class TestGlobalStateBuilder:
    """Test global state builder functions."""

    def test_get_state_builder(self):
        """Test get_state_builder returns StateBuilder instance."""
        builder = get_state_builder()
        assert isinstance(builder, StateBuilder)

        # Should return the same instance
        builder2 = get_state_builder()
        assert builder is builder2
