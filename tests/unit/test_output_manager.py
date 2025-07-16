"""Tests for OutputManager."""

from pathlib import Path
from unittest.mock import MagicMock, patch


from pidgin.io.output_manager import OutputManager


class TestOutputManager:
    """Test OutputManager functionality."""

    def test_init_default_base_dir(self):
        """Test initialization with default base directory."""
        with patch("pidgin.io.paths.get_output_dir") as mock_get_output_dir:
            mock_get_output_dir.return_value = Path("/test/output")

            manager = OutputManager()

            assert manager.base_dir == Path("/test/output")
            mock_get_output_dir.assert_called_once()

    def test_init_custom_base_dir(self):
        """Test initialization with custom base directory."""
        custom_dir = "/custom/path"
        manager = OutputManager(base_dir=custom_dir)

        assert manager.base_dir == Path(custom_dir)

    def test_create_conversation_dir_no_id(self, tmp_path):
        """Test creating conversation directory without providing ID."""
        manager = OutputManager(base_dir=str(tmp_path))

        # Mock datetime to make the test deterministic
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d": "2024-01-15",
            "%H%M%S": "143045",
        }[fmt]

        with patch("pidgin.io.output_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # Mock random choices to make test deterministic
            with patch("pidgin.io.output_manager.random.choices") as mock_choices:
                mock_choices.return_value = ["a", "b", "c", "d", "e"]

                conv_id, conv_dir = manager.create_conversation_dir()

                expected_id = "143045_abcde"
                expected_path = tmp_path / "conversations" / "2024-01-15" / expected_id

                assert conv_id == expected_id
                assert conv_dir == expected_path
                assert conv_dir.exists()
                assert conv_dir.is_dir()

    def test_create_conversation_dir_with_id(self, tmp_path):
        """Test creating conversation directory with provided ID."""
        manager = OutputManager(base_dir=str(tmp_path))
        custom_id = "test_conversation_123"

        mock_now = MagicMock()
        mock_now.strftime.return_value = "2024-01-15"

        with patch("pidgin.io.output_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            conv_id, conv_dir = manager.create_conversation_dir(custom_id)

            expected_path = tmp_path / "conversations" / "2024-01-15" / custom_id

            assert conv_id == custom_id
            assert conv_dir == expected_path
            assert conv_dir.exists()
            assert conv_dir.is_dir()

    def test_create_conversation_dir_creates_parent_dirs(self, tmp_path):
        """Test that conversation directory creation creates parent directories."""
        manager = OutputManager(base_dir=str(tmp_path))

        # Verify the conversations directory doesn't exist initially
        conversations_dir = tmp_path / "conversations"
        assert not conversations_dir.exists()

        mock_now = MagicMock()
        mock_now.strftime.return_value = "2024-01-15"

        with patch("pidgin.io.output_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            conv_id, conv_dir = manager.create_conversation_dir("test_id")

            # Verify all parent directories were created
            assert conversations_dir.exists()
            assert (conversations_dir / "2024-01-15").exists()
            assert conv_dir.exists()

    def test_create_conversation_dir_exists_ok(self, tmp_path):
        """Test that creating a directory that already exists doesn't fail."""
        manager = OutputManager(base_dir=str(tmp_path))

        mock_now = MagicMock()
        mock_now.strftime.return_value = "2024-01-15"

        with patch("pidgin.io.output_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # Create the directory first time
            conv_id1, conv_dir1 = manager.create_conversation_dir("same_id")

            # Create the same directory again - should not fail
            conv_id2, conv_dir2 = manager.create_conversation_dir("same_id")

            assert conv_id1 == conv_id2 == "same_id"
            assert conv_dir1 == conv_dir2
            assert conv_dir1.exists()
