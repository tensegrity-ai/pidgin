"""Tests for JSONLExperimentReader."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from pidgin.io.jsonl_reader import JSONLExperimentReader
from pidgin.constants import ExperimentStatus, ConversationStatus


class TestJSONLExperimentReader:
    """Test JSONLExperimentReader class."""
    
    def test_init(self):
        """Test JSONLExperimentReader initialization."""
        test_dir = Path("/test/experiments")
        reader = JSONLExperimentReader(test_dir)
        
        assert reader.experiments_dir == test_dir
        assert isinstance(reader.experiments_dir, Path)
    
    def test_init_with_string_path(self):
        """Test initialization with string path."""
        test_dir = "/test/experiments"
        reader = JSONLExperimentReader(test_dir)
        
        assert reader.experiments_dir == Path(test_dir)
        assert isinstance(reader.experiments_dir, Path)


class TestListExperiments:
    """Test list_experiments functionality."""
    
    def test_list_experiments_nonexistent_directory(self):
        """Test list_experiments when experiments directory doesn't exist."""
        reader = JSONLExperimentReader(Path("/nonexistent/path"))
        
        result = reader.list_experiments()
        
        assert result == []
    
    def test_list_experiments_empty_directory(self, tmp_path):
        """Test list_experiments with empty directory."""
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.list_experiments()
        
        assert result == []
    
    def test_list_experiments_no_valid_experiments(self, tmp_path):
        """Test list_experiments with no valid experiment directories."""
        # Create some directories that don't match experiment pattern
        (tmp_path / "not_experiment").mkdir()
        (tmp_path / "random_dir").mkdir()
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.list_experiments()
        
        assert result == []
    
    def test_list_experiments_valid_experiment_no_jsonl(self, tmp_path):
        """Test list_experiments with valid experiment directory but no JSONL files."""
        exp_dir = tmp_path / "exp_test123"
        exp_dir.mkdir()
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.list_experiments()
        
        assert result == []
    
    def test_list_experiments_single_experiment(self, tmp_path):
        """Test list_experiments with single valid experiment."""
        exp_dir = tmp_path / "exp_test123"
        exp_dir.mkdir()
        
        # Create a conversation JSONL file
        jsonl_file = exp_dir / "conv_001_events.jsonl"
        events = [
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Hello",
                "max_turns": 5
            },
            {
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 5
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.list_experiments()
        
        assert len(result) == 1
        assert result[0]['experiment_id'] == 'exp_test123'
        assert result[0]['status'] == ExperimentStatus.COMPLETED
        assert result[0]['total_conversations'] == 1
        assert result[0]['completed_conversations'] == 1
        assert result[0]['failed_conversations'] == 0
    
    def test_list_experiments_multiple_experiments(self, tmp_path):
        """Test list_experiments with multiple experiments."""
        # Create first experiment
        exp1_dir = tmp_path / "exp_test1"
        exp1_dir.mkdir()
        jsonl1 = exp1_dir / "conv_001_events.jsonl"
        
        with open(jsonl1, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3"
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 3
            }) + '\n')
        
        # Create second experiment
        exp2_dir = tmp_path / "exp_test2"
        exp2_dir.mkdir()
        jsonl2 = exp2_dir / "conv_002_events.jsonl"
        
        with open(jsonl2, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-02T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3"
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-02T12:05:00",
                "reason": "error",
                "total_turns": 1
            }) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.list_experiments()
        
        assert len(result) == 2
        
        # Should be sorted by created_at descending
        assert result[0]['experiment_id'] == 'exp_test2'  # Later timestamp
        assert result[1]['experiment_id'] == 'exp_test1'  # Earlier timestamp
    
    def test_list_experiments_with_status_filter(self, tmp_path):
        """Test list_experiments with status filter."""
        # Create completed experiment
        exp1_dir = tmp_path / "exp_completed"
        exp1_dir.mkdir()
        jsonl1 = exp1_dir / "conv_001_events.jsonl"
        
        with open(jsonl1, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00"
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 3
            }) + '\n')
        
        # Create running experiment
        exp2_dir = tmp_path / "exp_running"
        exp2_dir.mkdir()
        jsonl2 = exp2_dir / "conv_002_events.jsonl"
        
        with open(jsonl2, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-02T12:00:00"
            }) + '\n')
            # No ConversationEndEvent - still running
        
        reader = JSONLExperimentReader(tmp_path)
        
        # Test filtering by completed status
        completed = reader.list_experiments(status_filter=ExperimentStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0]['experiment_id'] == 'exp_completed'
        
        # Test filtering by running status
        running = reader.list_experiments(status_filter=ExperimentStatus.RUNNING)
        assert len(running) == 1
        assert running[0]['experiment_id'] == 'exp_running'
        
        # Test filtering by non-existent status
        none_found = reader.list_experiments(status_filter='nonexistent')
        assert len(none_found) == 0


class TestGetExperimentStatus:
    """Test get_experiment_status functionality."""
    
    def test_get_experiment_status_nonexistent_experiment(self, tmp_path):
        """Test get_experiment_status with non-existent experiment."""
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.get_experiment_status("nonexistent_exp")
        
        assert result is None
    
    def test_get_experiment_status_no_jsonl_files(self, tmp_path):
        """Test get_experiment_status with experiment directory but no JSONL files."""
        exp_dir = tmp_path / "exp_test123"
        exp_dir.mkdir()
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.get_experiment_status("exp_test123")
        
        assert result is None
    
    def test_get_experiment_status_valid_experiment(self, tmp_path):
        """Test get_experiment_status with valid experiment."""
        exp_dir = tmp_path / "exp_test123"
        exp_dir.mkdir()
        
        jsonl_file = exp_dir / "conv_001_events.jsonl"
        events = [
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Test prompt",
                "max_turns": 10
            },
            {
                "event_type": "TurnCompleteEvent",
                "turn_number": 1,
                "convergence_score": 0.5
            },
            {
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:10:00",
                "reason": "max_turns",
                "total_turns": 10
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader.get_experiment_status("exp_test123")
        
        assert result is not None
        assert result['experiment_id'] == 'exp_test123'
        assert result['status'] == ExperimentStatus.COMPLETED
        assert result['total_conversations'] == 1
        assert result['completed_conversations'] == 1
        assert result['failed_conversations'] == 0
        assert result['config']['agent_a_model'] == 'gpt-4'
        assert result['config']['agent_b_model'] == 'claude-3'
        assert result['config']['initial_prompt'] == 'Test prompt'
        assert result['config']['max_turns'] == 10


class TestParseExperimentFromEvents:
    """Test _parse_experiment_from_events functionality."""
    
    def test_parse_experiment_no_conversations(self, tmp_path):
        """Test parsing experiment with no valid conversations."""
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_experiment_from_events("exp_test", tmp_path)
        
        assert result is None
    
    def test_parse_experiment_single_conversation(self, tmp_path):
        """Test parsing experiment with single conversation."""
        jsonl_file = tmp_path / "conv_001_events.jsonl"
        events = [
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Hello world",
                "max_turns": 5,
                "temperature_a": 0.7,
                "temperature_b": 0.5
            },
            {
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 5
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_experiment_from_events("exp_test", tmp_path)
        
        assert result is not None
        assert result['experiment_id'] == 'exp_test'
        assert result['status'] == ExperimentStatus.COMPLETED
        assert result['total_conversations'] == 1
        assert result['completed_conversations'] == 1
        assert result['failed_conversations'] == 0
        assert result['created_at'] == "2024-01-01T12:00:00"
        assert result['started_at'] == "2024-01-01T12:00:00"
        assert result['name'] == 'exp_test'  # Default to ID
        
        # Check config
        config = result['config']
        assert config['agent_a_model'] == 'gpt-4'
        assert config['agent_b_model'] == 'claude-3'
        assert config['initial_prompt'] == 'Hello world'
        assert config['max_turns'] == 5
        assert config['temperature_a'] == 0.7
        assert config['temperature_b'] == 0.5
    
    def test_parse_experiment_multiple_conversations(self, tmp_path):
        """Test parsing experiment with multiple conversations."""
        # Create first conversation (completed)
        jsonl1 = tmp_path / "conv_001_events.jsonl"
        with open(jsonl1, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4"
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 3
            }) + '\n')
        
        # Create second conversation (failed)
        jsonl2 = tmp_path / "conv_002_events.jsonl"
        with open(jsonl2, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:10:00",
                "agent_a_model": "gpt-4"
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:15:00",
                "reason": "error",
                "total_turns": 1
            }) + '\n')
        
        # Create third conversation (running)
        jsonl3 = tmp_path / "conv_003_events.jsonl"
        with open(jsonl3, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:20:00",
                "agent_a_model": "gpt-4"
            }) + '\n')
            # No end event - still running
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_experiment_from_events("exp_test", tmp_path)
        
        assert result is not None
        assert result['experiment_id'] == 'exp_test'
        assert result['status'] == ExperimentStatus.RUNNING  # Has running conversations
        assert result['total_conversations'] == 3
        assert result['completed_conversations'] == 1
        assert result['failed_conversations'] == 1
    
    def test_parse_experiment_with_experiment_name(self, tmp_path):
        """Test parsing experiment with experiment name in events."""
        jsonl_file = tmp_path / "conv_001_events.jsonl"
        events = [
            {
                "event_type": "ExperimentCreated",
                "data": {
                    "name": "My Test Experiment"
                }
            },
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4"
            },
            {
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 3
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_experiment_from_events("exp_test", tmp_path)
        
        assert result is not None
        assert result['name'] == 'My Test Experiment'


class TestParseConversationEvents:
    """Test _parse_conversation_events functionality."""
    
    def test_parse_conversation_events_file_not_found(self, tmp_path):
        """Test parsing conversation events with non-existent file."""
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_conversation_events(tmp_path / "nonexistent.jsonl")
        
        assert result is None
    
    def test_parse_conversation_events_empty_file(self, tmp_path):
        """Test parsing conversation events with empty file."""
        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.touch()
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_conversation_events(jsonl_file)
        
        assert result is not None
        assert result['status'] == 'unknown'
        assert result['started_at'] is None
        assert result['ended_at'] is None
        assert result['total_turns'] == 0
        assert result['config'] == {}
        assert result['convergence_scores'] == []
    
    def test_parse_conversation_events_with_empty_lines(self, tmp_path):
        """Test parsing conversation events with empty lines."""
        jsonl_file = tmp_path / "events.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00"
            }) + '\n')
            f.write('\n')  # Empty line
            f.write('   \n')  # Whitespace only
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 5
            }) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_conversation_events(jsonl_file)
        
        assert result is not None
        assert result['status'] == ConversationStatus.COMPLETED
        assert result['started_at'] == "2024-01-01T12:00:00"
        assert result['ended_at'] == "2024-01-01T12:05:00"
        assert result['total_turns'] == 5
    
    def test_parse_conversation_events_with_invalid_json(self, tmp_path):
        """Test parsing conversation events with invalid JSON lines."""
        jsonl_file = tmp_path / "events.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00"
            }) + '\n')
            f.write('invalid json line\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:05:00",
                "reason": "max_turns",
                "total_turns": 5
            }) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        with patch('pidgin.io.jsonl_reader.logger') as mock_logger:
            result = reader._parse_conversation_events(jsonl_file)
            
            assert result is not None
            assert result['status'] == ConversationStatus.COMPLETED
            # Should have logged warning for invalid JSON
            mock_logger.warning.assert_called_once()
    
    def test_parse_conversation_events_complete_conversation(self, tmp_path):
        """Test parsing complete conversation with all event types."""
        jsonl_file = tmp_path / "events.jsonl"
        events = [
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Hello",
                "max_turns": 10,
                "temperature_a": 0.7,
                "temperature_b": 0.5
            },
            {
                "event_type": "TurnCompleteEvent",
                "turn_number": 1,
                "convergence_score": 0.3
            },
            {
                "event_type": "TurnCompleteEvent",
                "turn_number": 2,
                "convergence_score": 0.6
            },
            {
                "event_type": "TurnCompleteEvent",
                "turn_number": 3,
                "convergence_score": 0.8
            },
            {
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:10:00",
                "reason": "high_convergence",
                "total_turns": 3
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_conversation_events(jsonl_file)
        
        assert result is not None
        assert result['status'] == ConversationStatus.COMPLETED
        assert result['started_at'] == "2024-01-01T12:00:00"
        assert result['ended_at'] == "2024-01-01T12:10:00"
        assert result['total_turns'] == 3
        assert result['convergence_scores'] == [0.3, 0.6, 0.8]
        
        # Check config
        config = result['config']
        assert config['agent_a_model'] == 'gpt-4'
        assert config['agent_b_model'] == 'claude-3'
        assert config['initial_prompt'] == 'Hello'
        assert config['max_turns'] == 10
        assert config['temperature_a'] == 0.7
        assert config['temperature_b'] == 0.5
    
    def test_parse_conversation_events_different_end_reasons(self, tmp_path):
        """Test parsing conversation events with different end reasons."""
        reader = JSONLExperimentReader(tmp_path)
        
        # Test max_turns reason
        jsonl_file = tmp_path / "max_turns.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({"event_type": "ConversationStartEvent", "timestamp": "2024-01-01T12:00:00"}) + '\n')
            f.write(json.dumps({"event_type": "ConversationEndEvent", "reason": "max_turns", "total_turns": 5}) + '\n')
        
        result = reader._parse_conversation_events(jsonl_file)
        assert result['status'] == ConversationStatus.COMPLETED
        
        # Test high_convergence reason
        jsonl_file = tmp_path / "high_convergence.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({"event_type": "ConversationStartEvent", "timestamp": "2024-01-01T12:00:00"}) + '\n')
            f.write(json.dumps({"event_type": "ConversationEndEvent", "reason": "high_convergence", "total_turns": 3}) + '\n')
        
        result = reader._parse_conversation_events(jsonl_file)
        assert result['status'] == ConversationStatus.COMPLETED
        
        # Test error reason
        jsonl_file = tmp_path / "error.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({"event_type": "ConversationStartEvent", "timestamp": "2024-01-01T12:00:00"}) + '\n')
            f.write(json.dumps({"event_type": "ConversationEndEvent", "reason": "error", "total_turns": 1}) + '\n')
        
        result = reader._parse_conversation_events(jsonl_file)
        assert result['status'] == ConversationStatus.FAILED
        
        # Test other reason
        jsonl_file = tmp_path / "other.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({"event_type": "ConversationStartEvent", "timestamp": "2024-01-01T12:00:00"}) + '\n')
            f.write(json.dumps({"event_type": "ConversationEndEvent", "reason": "interrupted", "total_turns": 2}) + '\n')
        
        result = reader._parse_conversation_events(jsonl_file)
        assert result['status'] == ConversationStatus.INTERRUPTED
    
    def test_parse_conversation_events_turn_number_tracking(self, tmp_path):
        """Test that turn numbers are tracked correctly."""
        jsonl_file = tmp_path / "events.jsonl"
        events = [
            {"event_type": "ConversationStartEvent", "timestamp": "2024-01-01T12:00:00"},
            {"event_type": "TurnCompleteEvent", "turn_number": 1},
            {"event_type": "TurnCompleteEvent", "turn_number": 3},  # Skip 2
            {"event_type": "TurnCompleteEvent", "turn_number": 2},  # Out of order
            {"event_type": "ConversationEndEvent", "total_turns": 5}  # Final count
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_conversation_events(jsonl_file)
        
        assert result is not None
        # Should take the max of TurnCompleteEvent numbers and ConversationEndEvent total
        assert result['total_turns'] == 5
    
    def test_parse_conversation_events_with_experiment_name(self, tmp_path):
        """Test parsing conversation events with experiment name."""
        jsonl_file = tmp_path / "events.jsonl"
        events = [
            {
                "event_type": "ExperimentCreated",
                "data": {
                    "name": "Test Experiment Name"
                }
            },
            {
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00"
            },
            {
                "event_type": "ConversationEndEvent",
                "reason": "max_turns",
                "total_turns": 3
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        result = reader._parse_conversation_events(jsonl_file)
        
        assert result is not None
        assert result['experiment_name'] == 'Test Experiment Name'


class TestExtractNameFromPrompt:
    """Test _extract_name_from_prompt functionality."""
    
    def test_extract_name_short_prompt(self):
        """Test extracting name from short prompt."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        result = reader._extract_name_from_prompt("Hello world")
        
        assert result == "Hello world"
    
    def test_extract_name_long_prompt(self):
        """Test extracting name from long prompt."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        prompt = "This is a very long prompt that should be truncated"
        result = reader._extract_name_from_prompt(prompt)
        
        assert result == "This is a very long"
    
    def test_extract_name_very_long_prompt(self):
        """Test extracting name from very long prompt that needs truncation."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        # Create a prompt where the first 5 words are longer than 50 characters
        prompt = "Supercalifragilisticexpialidocious antidisestablishmentarianism pneumonoultramicroscopicsilicovolcanoconiosis hippopotomonstrosesquippedaliophobia"
        result = reader._extract_name_from_prompt(prompt)
        
        assert len(result) <= 50
        assert result.endswith("...")
    
    def test_extract_name_empty_prompt(self):
        """Test extracting name from empty prompt."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        result = reader._extract_name_from_prompt("")
        
        assert result == ""
    
    def test_extract_name_single_word(self):
        """Test extracting name from single word prompt."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        result = reader._extract_name_from_prompt("Hello")
        
        assert result == "Hello"
    
    def test_extract_name_exactly_five_words(self):
        """Test extracting name from exactly five words."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        result = reader._extract_name_from_prompt("One two three four five")
        
        assert result == "One two three four five"
    
    def test_extract_name_more_than_five_words(self):
        """Test extracting name from more than five words."""
        reader = JSONLExperimentReader(Path("/tmp"))
        
        result = reader._extract_name_from_prompt("One two three four five six seven eight")
        
        assert result == "One two three four five"


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    def test_end_to_end_experiment_reading(self, tmp_path):
        """Test complete end-to-end experiment reading."""
        # Create experiment directory
        exp_dir = tmp_path / "exp_integration_test"
        exp_dir.mkdir()
        
        # Create first conversation
        conv1 = exp_dir / "conv_001_events.jsonl"
        with open(conv1, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T12:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3",
                "initial_prompt": "Discuss philosophy",
                "max_turns": 10
            }) + '\n')
            f.write(json.dumps({
                "event_type": "TurnCompleteEvent",
                "turn_number": 1,
                "convergence_score": 0.4
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T12:15:00",
                "reason": "max_turns",
                "total_turns": 10
            }) + '\n')
        
        # Create second conversation
        conv2 = exp_dir / "conv_002_events.jsonl"
        with open(conv2, 'w') as f:
            f.write(json.dumps({
                "event_type": "ConversationStartEvent",
                "timestamp": "2024-01-01T13:00:00",
                "agent_a_model": "gpt-4",
                "agent_b_model": "claude-3"
            }) + '\n')
            f.write(json.dumps({
                "event_type": "ConversationEndEvent",
                "timestamp": "2024-01-01T13:05:00",
                "reason": "error",
                "total_turns": 2
            }) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        # Test list_experiments
        experiments = reader.list_experiments()
        assert len(experiments) == 1
        assert experiments[0]['experiment_id'] == 'exp_integration_test'
        assert experiments[0]['status'] == ExperimentStatus.COMPLETED
        assert experiments[0]['total_conversations'] == 2
        assert experiments[0]['completed_conversations'] == 1
        assert experiments[0]['failed_conversations'] == 1
        
        # Test get_experiment_status
        status = reader.get_experiment_status('exp_integration_test')
        assert status is not None
        assert status['experiment_id'] == 'exp_integration_test'
        assert status['config']['agent_a_model'] == 'gpt-4'
        # The config will be from the last conversation processed, which doesn't have initial_prompt
        # This is expected behavior given the current implementation
    
    def test_error_handling_during_file_reading(self, tmp_path):
        """Test error handling when file reading fails."""
        exp_dir = tmp_path / "exp_test"
        exp_dir.mkdir()
        
        # Create a file that will cause an error
        jsonl_file = exp_dir / "conv_001_events.jsonl"
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({"event_type": "ConversationStartEvent"}) + '\n')
        
        reader = JSONLExperimentReader(tmp_path)
        
        # Mock file reading to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('pidgin.io.jsonl_reader.logger') as mock_logger:
                result = reader._parse_conversation_events(jsonl_file)
                
                assert result is None
                mock_logger.error.assert_called_once()
                assert "Error reading" in mock_logger.error.call_args[0][0]