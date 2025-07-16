"""Tests for path utilities."""

from pathlib import Path
from unittest.mock import patch


from pidgin.io.paths import (
    get_chats_database_path,
    get_conversations_dir,
    get_database_path,
    get_experiments_dir,
    get_output_dir,
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

    def test_pidgin_original_cwd_not_exists(self, monkeypatch, tmp_path):
        """Test when PIDGIN_ORIGINAL_CWD doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"
        pwd_dir = tmp_path / "pwd_dir"
        pwd_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(nonexistent_dir))
        monkeypatch.setenv("PWD", str(pwd_dir))

        output_dir = get_output_dir()
        assert output_dir == pwd_dir / "pidgin_output"

    def test_pwd_not_exists(self, monkeypatch, tmp_path):
        """Test when PWD doesn't exist."""
        nonexistent_pwd = tmp_path / "nonexistent_pwd"
        cwd_dir = tmp_path / "cwd_dir"
        cwd_dir.mkdir()

        monkeypatch.delenv("PIDGIN_ORIGINAL_CWD", raising=False)
        monkeypatch.setenv("PWD", str(nonexistent_pwd))
        monkeypatch.chdir(cwd_dir)

        output_dir = get_output_dir()
        assert output_dir == cwd_dir / "pidgin_output"

    def test_no_debug_output(self, monkeypatch, tmp_path, capsys):
        """Test no debug output when PIDGIN_DEBUG is not set."""
        test_dir = tmp_path / "no_debug_test"
        test_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))
        monkeypatch.delenv("PIDGIN_DEBUG", raising=False)

        output_dir = get_output_dir()

        captured = capsys.readouterr()
        assert "[DEBUG]" not in captured.out

    def test_empty_environment_variables(self, monkeypatch, tmp_path):
        """Test behavior with empty environment variables."""
        cwd_dir = tmp_path / "empty_env_test"
        cwd_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", "")
        monkeypatch.setenv("PWD", "")
        monkeypatch.chdir(cwd_dir)

        output_dir = get_output_dir()
        assert output_dir == cwd_dir / "pidgin_output"

    def test_all_debug_fields(self, monkeypatch, tmp_path, capsys):
        """Test all debug output fields are printed."""
        test_dir = tmp_path / "all_debug_test"
        test_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))
        monkeypatch.setenv("PWD", str(test_dir))
        monkeypatch.setenv("PIDGIN_DEBUG", "1")
        monkeypatch.chdir(test_dir)

        output_dir = get_output_dir()

        captured = capsys.readouterr()
        assert "[DEBUG] Output directory:" in captured.out
        assert "[DEBUG] PIDGIN_ORIGINAL_CWD:" in captured.out
        assert "[DEBUG] PWD:" in captured.out
        assert "[DEBUG] os.getcwd():" in captured.out


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
        assert (
            db_path == tmp_path / "pidgin_output" / "experiments" / "experiments.duckdb"
        )

    def test_get_chats_database_path(self):
        """Test get_chats_database_path."""
        db_path = get_chats_database_path()

        # Should be in home directory
        assert db_path == Path.home() / ".pidgin" / "chats.duckdb"
        assert db_path.parent == Path.home() / ".pidgin"

    def test_get_experiments_dir_calls_get_output_dir(self):
        """Test that get_experiments_dir calls get_output_dir."""
        with patch("pidgin.io.paths.get_output_dir") as mock_get_output_dir:
            mock_output_dir = Path("/test/output")
            mock_get_output_dir.return_value = mock_output_dir

            result = get_experiments_dir()

            assert result == mock_output_dir / "experiments"
            mock_get_output_dir.assert_called_once()

    def test_get_conversations_dir_calls_get_output_dir(self):
        """Test that get_conversations_dir calls get_output_dir."""
        with patch("pidgin.io.paths.get_output_dir") as mock_get_output_dir:
            mock_output_dir = Path("/test/output")
            mock_get_output_dir.return_value = mock_output_dir

            result = get_conversations_dir()

            assert result == mock_output_dir / "conversations"
            mock_get_output_dir.assert_called_once()

    def test_get_database_path_calls_get_experiments_dir(self):
        """Test that get_database_path calls get_experiments_dir."""
        with patch("pidgin.io.paths.get_experiments_dir") as mock_get_experiments_dir:
            mock_experiments_dir = Path("/test/experiments")
            mock_get_experiments_dir.return_value = mock_experiments_dir

            result = get_database_path()

            assert result == mock_experiments_dir / "experiments.duckdb"
            mock_get_experiments_dir.assert_called_once()

    def test_get_chats_database_path_calls_home(self):
        """Test that get_chats_database_path calls Path.home()."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home_dir = Path("/test/home")
            mock_home.return_value = mock_home_dir

            result = get_chats_database_path()

            assert result == mock_home_dir / ".pidgin" / "chats.duckdb"
            mock_home.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios across multiple functions."""

    def test_all_paths_consistent(self, monkeypatch, tmp_path):
        """Test that all path functions are consistent with each other."""
        test_dir = tmp_path / "integration_test"
        test_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))

        output_dir = get_output_dir()
        experiments_dir = get_experiments_dir()
        conversations_dir = get_conversations_dir()
        database_path = get_database_path()

        # Check consistency
        assert output_dir == test_dir / "pidgin_output"
        assert experiments_dir == output_dir / "experiments"
        assert conversations_dir == output_dir / "conversations"
        assert database_path == experiments_dir / "experiments.duckdb"

    def test_path_structure_hierarchy(self, monkeypatch, tmp_path):
        """Test that the path structure follows the expected hierarchy."""
        test_dir = tmp_path / "hierarchy_test"
        test_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))

        output_dir = get_output_dir()
        experiments_dir = get_experiments_dir()
        conversations_dir = get_conversations_dir()
        database_path = get_database_path()

        # Check hierarchy
        assert experiments_dir.parent == output_dir
        assert conversations_dir.parent == output_dir
        assert database_path.parent == experiments_dir

    def test_chats_database_separate_from_experiments(self, monkeypatch, tmp_path):
        """Test that chats database is separate from experiments structure."""
        test_dir = tmp_path / "separate_test"
        test_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(test_dir))

        chats_db = get_chats_database_path()
        experiments_db = get_database_path()

        # Chats database should be in home directory
        assert chats_db == Path.home() / ".pidgin" / "chats.duckdb"

        # Should be completely separate from experiments path
        assert not str(chats_db).startswith(str(experiments_db.parent))
        assert not str(experiments_db).startswith(str(chats_db.parent))


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_path_with_spaces_and_special_chars(self, monkeypatch, tmp_path):
        """Test paths with spaces and special characters."""
        special_dir = tmp_path / "path with spaces & special chars"
        special_dir.mkdir()

        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", str(special_dir))

        output_dir = get_output_dir()
        assert output_dir == special_dir / "pidgin_output"

    def test_relative_paths_in_environment(self, monkeypatch, tmp_path):
        """Test behavior with relative paths in environment variables."""
        test_dir = tmp_path / "relative_test"
        test_dir.mkdir()

        # Use relative path notation
        relative_path = f"./{test_dir.name}"

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PIDGIN_ORIGINAL_CWD", relative_path)

        output_dir = get_output_dir()
        assert output_dir == Path(relative_path) / "pidgin_output"
