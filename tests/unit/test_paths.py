# tests/unit/test_paths.py
"""Test path utility functions."""

import pytest
import os
from pathlib import Path
from pidgin.io.paths import (
    get_output_dir, get_experiments_dir, get_conversations_dir,
    get_database_path, get_chats_database_path
)


class TestGetOutputDir:
    """Test get_output_dir function."""
    
    def test_with_pidgin_original_cwd(self, monkeypatch, tmp_path):
        """Test with PIDGIN_ORIGINAL_CWD set."""
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()
        
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))
        
        output_dir = get_output_dir()
        assert output_dir == test_dir / "pidgin_output"
    
    def test_with_pwd(self, monkeypatch, tmp_path):
        """Test with PWD set."""
        test_dir = tmp_path / "test_pwd"
        test_dir.mkdir()
        
        # Ensure PIDGIN_ORIGINAL_CWD is not set
        monkeypatch.delenv("PIDGIN_ORIGINAL_CWD", raising=False)
        monkeypatch.setenv("PWD", str(test_dir))
        
        output_dir = get_output_dir()
        assert output_dir == test_dir / "pidgin_output"
    
    def test_fallback_to_cwd(self, monkeypatch, tmp_path):
        """Test fallback to os.getcwd()."""
        test_dir = tmp_path / "test_cwd"
        test_dir.mkdir()
        
        # Clear environment variables
        monkeypatch.delenv("PIDGIN_ORIGINAL_CWD", raising=False)
        monkeypatch.delenv("PWD", raising=False)
        
        # Mock os.getcwd()
        monkeypatch.chdir(test_dir)
        
        output_dir = get_output_dir()
        assert output_dir == test_dir / "pidgin_output"
    
    def test_priority_order(self, monkeypatch, tmp_path):
        """Test environment variable priority order."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir3 = tmp_path / "dir3"
        
        for d in [dir1, dir2, dir3]:
            d.mkdir()
        
        # Set all three
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(dir1))
        monkeypatch.setenv("PWD", str(dir2))
        monkeypatch.chdir(dir3)
        
        # Should use PIDGIN_ORIGINAL_CWD first
        output_dir = get_output_dir()
        assert output_dir == dir1 / "pidgin_output"
    
    def test_debug_output(self, monkeypatch, tmp_path, capsys):
        """Test debug output when PIDGIN_DEBUG is set."""
        test_dir = tmp_path / "debug_test"
        test_dir.mkdir()
        
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))
        monkeypatch.setenv("PIDGIN_DEBUG", "1")
        
        output_dir = get_output_dir()
        
        captured = capsys.readouterr()
        assert "[DEBUG] Output directory:" in captured.out
        assert str(test_dir / "pidgin_output") in captured.out


class TestOtherPathFunctions:
    """Test other path utility functions."""
    
    def test_get_experiments_dir(self, monkeypatch, tmp_path):
        """Test get_experiments_dir."""
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(tmp_path))
        
        exp_dir = get_experiments_dir()
        assert exp_dir == tmp_path / "pidgin_output" / "experiments"
    
    def test_get_conversations_dir(self, monkeypatch, tmp_path):
        """Test get_conversations_dir."""
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(tmp_path))
        
        conv_dir = get_conversations_dir()
        assert conv_dir == tmp_path / "pidgin_output" / "conversations"
    
    def test_get_database_path(self, monkeypatch, tmp_path):
        """Test get_database_path."""
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(tmp_path))
        
        db_path = get_database_path()
        assert db_path == tmp_path / "pidgin_output" / "experiments" / "experiments.duckdb"
    
    def test_get_chats_database_path(self):
        """Test get_chats_database_path."""
        db_path = get_chats_database_path()
        
        # Should be in home directory
        assert db_path == Path.home() / ".pidgin" / "chats.duckdb"
        assert db_path.parent == Path.home() / ".pidgin"