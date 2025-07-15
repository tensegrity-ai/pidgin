"""Tests for the Monitor class."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from rich.console import Console

from pidgin.monitor.monitor import Monitor
from pidgin.constants import ExperimentStatus, ConversationStatus


def render_to_text(renderable):
    """Helper to render Rich objects to text for testing."""
    console = Console(width=120, legacy_windows=False)
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


@pytest.fixture
def temp_experiments_dir():
    """Create temporary experiments directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_experiment_dir(temp_experiments_dir):
    """Create a sample experiment directory with files."""
    exp_dir = temp_experiments_dir / "test_experiment"
    exp_dir.mkdir()
    
    # Create manifest.json
    manifest = {
        "experiment_id": "test_experiment",
        "name": "Test Experiment",
        "status": "running",
        "conversations": {
            "conv_1": {
                "status": "completed",
                "last_updated": datetime.now(timezone.utc).isoformat()
            },
            "conv_2": {
                "status": "failed",
                "error": "Rate limit exceeded",
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        }
    }
    with open(exp_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)
    
    # Create JSONL file with events
    # Use timezone-aware timestamps
    now = datetime.now(timezone.utc)
    events = [
        {
            "event_type": "APIErrorEvent",
            "provider": "openai",
            "error_type": "rate_limit",
            "timestamp": now.isoformat()
        },
        {
            "event_type": "ErrorEvent",
            "error_type": "auth_error",
            "provider": "anthropic",
            "timestamp": (now - timedelta(minutes=5)).isoformat()
        },
        {
            "event_type": "MessageSentEvent",
            "timestamp": now.isoformat()
        }
    ]
    
    with open(exp_dir / "events.jsonl", "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    
    return exp_dir


@pytest.fixture
def monitor(temp_experiments_dir):
    """Create a Monitor instance with mocked dependencies."""
    # Create a test console with wider width to accommodate full table
    test_console = Console(width=120, legacy_windows=False)
    
    with patch('pidgin.monitor.monitor.get_experiments_dir', return_value=temp_experiments_dir), \
         patch('pidgin.monitor.monitor.get_state_builder') as mock_state_builder:
        
        # Mock state builder
        mock_builder = Mock()
        mock_builder.list_experiments = Mock(return_value=[])
        mock_builder.clear_cache = Mock()
        mock_state_builder.return_value = mock_builder
        
        monitor = Monitor(console_instance=test_console)
        # Ensure monitor uses the right directory and knows it exists
        monitor.exp_base = temp_experiments_dir
        monitor.no_output_dir = False
        return monitor


class TestMonitor:
    """Test Monitor functionality."""
    
    def test_initialization(self, monitor, temp_experiments_dir):
        """Test Monitor initializes correctly."""
        assert monitor.exp_base == temp_experiments_dir
        assert monitor.running is True
        assert monitor.state_builder is not None
    
    def test_tail_file_empty_file(self, monitor, temp_experiments_dir):
        """Test tailing an empty file."""
        empty_file = temp_experiments_dir / "empty.txt"
        empty_file.touch()
        
        result = monitor.tail_file(empty_file, lines=10)
        assert result == []
    
    def test_tail_file_nonexistent(self, monitor, temp_experiments_dir):
        """Test tailing a nonexistent file."""
        nonexistent = temp_experiments_dir / "nonexistent.txt"
        
        result = monitor.tail_file(nonexistent, lines=10)
        assert result == []
    
    def test_tail_file_with_content(self, monitor, temp_experiments_dir):
        """Test tailing a file with content."""
        test_file = temp_experiments_dir / "test.txt"
        lines = ["line1", "line2", "line3", "line4", "line5"]
        
        with open(test_file, "w") as f:
            f.write("\n".join(lines))
        
        result = monitor.tail_file(test_file, lines=3)
        assert len(result) <= 3
        assert "line5" in result
    
    def test_get_recent_errors_no_experiments(self, monitor, temp_experiments_dir):
        """Test getting recent errors when no experiments exist."""
        result = monitor.get_recent_errors(minutes=10)
        assert result == []
    
    def test_get_recent_errors_with_sample_data(self, monitor, sample_experiment_dir):
        """Test getting recent errors with sample data."""
        # The sample_experiment_dir is created inside temp_experiments_dir
        # which monitor is already using
        result = monitor.get_recent_errors(minutes=10)
        
        # Should find error events
        error_events = [e for e in result if e.get('event_type') in ['APIErrorEvent', 'ErrorEvent']]
        assert len(error_events) >= 1
        
        # Check that experiment_id is added
        for event in error_events:
            assert 'experiment_id' in event
            assert event['experiment_id'] == "test_experiment"
    
    def test_get_recent_errors_time_filtering(self, monitor, temp_experiments_dir):
        """Test that recent errors filters by time correctly."""
        exp_dir = temp_experiments_dir / "test_exp"
        exp_dir.mkdir()
        
        # Create events with different timestamps
        # Use timezone-aware timestamps
        old_event = {
            "event_type": "APIErrorEvent",
            "provider": "openai",
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        }
        recent_event = {
            "event_type": "ErrorEvent",
            "provider": "anthropic",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        with open(exp_dir / "events.jsonl", "w") as f:
            f.write(json.dumps(old_event) + "\n")
            f.write(json.dumps(recent_event) + "\n")
        
        # Should only get recent events
        result = monitor.get_recent_errors(minutes=10)
        assert len(result) == 1
        assert result[0]['provider'] == 'anthropic'
    
    def test_get_failed_conversations_no_experiments(self, monitor, temp_experiments_dir):
        """Test getting failed conversations when no experiments exist."""
        result = monitor.get_failed_conversations()
        assert result == []
    
    def test_get_failed_conversations_with_sample_data(self, monitor, sample_experiment_dir):
        """Test getting failed conversations with sample data."""
        result = monitor.get_failed_conversations()
        
        # Should find the failed conversation from sample data
        failed_convs = [c for c in result if c['conversation_id'] == 'conv_2']
        assert len(failed_convs) == 1
        assert failed_convs[0]['error'] == "Rate limit exceeded"
        assert failed_convs[0]['experiment_id'] == "test_experiment"
    
    def test_build_header(self, monitor):
        """Test building the header panel."""
        with patch('pidgin.monitor.monitor.datetime') as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2023-01-01 12:00:00"
            
            header = monitor.build_header()
            header_text = render_to_text(header)
            assert "PIDGIN MONITOR" in header_text
            assert "2023-01-01 12:00:00" in header_text
    
    def test_build_experiments_panel_no_experiments(self, monitor):
        """Test building experiments panel with no running experiments."""
        panel = monitor.build_experiments_panel([])
        panel_text = render_to_text(panel)
        assert "No active experiments" in panel_text
    
    def test_build_experiments_panel_with_experiments(self, monitor):
        """Test building experiments panel with mock experiments."""
        # Create mock experiment with all required attributes
        mock_conv = Mock()
        mock_conv.status = ConversationStatus.RUNNING
        mock_conv.current_turn = 5
        mock_conv.agent_a_model = "gpt-4"
        
        mock_exp = Mock()
        mock_exp.experiment_id = "test_exp_123"
        mock_exp.name = "Test Experiment"
        mock_exp.status = "running"  # Need to set status for filtering
        mock_exp.progress = (5, 10)  # completed, total
        mock_exp.completed_conversations = 5
        mock_exp.total_conversations = 10
        mock_exp.conversations = {"conv1": mock_conv}
        mock_exp.started_at = datetime.now() - timedelta(hours=1)
        
        # Add methods for token estimation
        monitor._estimate_tokens_for_experiment = Mock(return_value=1500)
        monitor._estimate_cost_for_experiment = Mock(return_value=0.45)
        
        panel = monitor.build_experiments_panel([mock_exp])
        panel_text = render_to_text(panel)
        assert "Test Experiment" in panel_text
        assert "5/10" in panel_text
    
    def test_build_errors_panel_no_errors(self, monitor):
        """Test building errors panel with no recent errors."""
        with patch.object(monitor, 'get_recent_errors', return_value=[]):
            panel = monitor.build_errors_panel()
            panel_text = render_to_text(panel)
            assert "No recent errors" in panel_text
    
    def test_build_errors_panel_with_errors(self, monitor):
        """Test building errors panel with recent errors."""
        mock_errors = [
            {
                "event_type": "APIErrorEvent",
                "provider": "openai",
                "error_type": "rate_limit",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event_type": "ErrorEvent",
                "provider": "anthropic",
                "error_type": "auth_error",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        with patch.object(monitor, 'get_recent_errors', return_value=mock_errors):
            panel = monitor.build_errors_panel()
            panel_text = render_to_text(panel)
            assert "Openai" in panel_text or "openai" in panel_text
            assert "Anthropic" in panel_text or "anthropic" in panel_text
    
    def test_build_conversations_panel_empty(self, monitor):
        """Test building conversations panel with no data."""
        panel = monitor.build_conversations_panel([])
        panel_text = render_to_text(panel)
        assert "No conversations found" in panel_text
    
    def test_get_experiment_states_calls_state_builder(self, monitor):
        """Test that get_experiment_states calls the state builder correctly."""
        mock_experiments = [Mock(), Mock()]
        monitor.state_builder.list_experiments.return_value = mock_experiments
        
        result = monitor.get_experiment_states()
        
        # Should clear cache and call list_experiments
        monitor.state_builder.clear_cache.assert_called_once()
        monitor.state_builder.list_experiments.assert_called_once_with(
            monitor.exp_base,
            status_filter=None
        )
        assert result == mock_experiments
    
    def test_build_display_integration(self, monitor):
        """Test that build_display integrates all components."""
        # Mock the individual panel builders
        with patch.object(monitor, 'get_experiment_states', return_value=[]), \
             patch.object(monitor, 'build_header', return_value=Mock()), \
             patch.object(monitor, 'build_errors_panel', return_value=Mock()), \
             patch.object(monitor, 'build_experiments_panel', return_value=Mock()), \
             patch.object(monitor, 'build_conversations_panel', return_value=Mock()):
            
            layout = monitor.build_display()
            
            # Should call all the builders
            monitor.get_experiment_states.assert_called_once()
            monitor.build_header.assert_called_once()
            monitor.build_errors_panel.assert_called_once()
            monitor.build_experiments_panel.assert_called_once()
            monitor.build_conversations_panel.assert_called_once()
            
            # Should return a layout
            assert layout is not None


class TestMonitorErrorHandling:
    """Test Monitor error handling scenarios."""
    
    def test_malformed_json_in_jsonl(self, monitor, temp_experiments_dir):
        """Test handling malformed JSON in JSONL files."""
        exp_dir = temp_experiments_dir / "test_exp"
        exp_dir.mkdir()
        
        # Create JSONL with malformed JSON
        # Use timezone-aware timestamp
        now = datetime.now(timezone.utc)
        with open(exp_dir / "events.jsonl", "w") as f:
            f.write('{"valid": "json"}\n')  # Valid JSON but not an error event
            f.write('malformed json line\n')  # Invalid JSON
            f.write(json.dumps({
                "another": "valid", 
                "event_type": "ErrorEvent",
                "timestamp": now.isoformat()
            }) + '\n')  # Valid error event
        
        # Should handle malformed JSON gracefully
        result = monitor.get_recent_errors(minutes=10)
        
        # Should only get valid error events with proper timestamps
        assert len(result) == 1
        assert result[0]['another'] == 'valid'
    
    def test_missing_manifest_file(self, monitor, temp_experiments_dir):
        """Test handling missing manifest files."""
        exp_dir = temp_experiments_dir / "test_exp"
        exp_dir.mkdir()
        
        # No manifest.json file
        result = monitor.get_failed_conversations()
        assert result == []
    
    def test_malformed_manifest_json(self, monitor, temp_experiments_dir):
        """Test handling malformed manifest JSON."""
        exp_dir = temp_experiments_dir / "test_exp"
        exp_dir.mkdir()
        
        # Create malformed manifest
        with open(exp_dir / "manifest.json", "w") as f:
            f.write("malformed json")
        
        # Should handle gracefully
        result = monitor.get_failed_conversations()
        assert result == []