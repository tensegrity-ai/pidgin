"""File reading utilities for the monitor."""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..io.logger import get_logger

logger = get_logger("file_reader")


class FileReader:
    """Handles file operations for the monitor."""

    @staticmethod
    def tail_file(file_path: Path, lines: int = 200) -> List[str]:
        """Get the last N lines from a file efficiently.

        Args:
            file_path: Path to the file
            lines: Number of lines to return

        Returns:
            List of the last N lines from the file
        """
        if not file_path.exists():
            return []

        try:
            # For small files, just read all lines
            file_size = file_path.stat().st_size
            if file_size < 100_000:  # Less than 100KB
                with open(file_path) as f:
                    all_lines = f.readlines()
                    return all_lines[-lines:] if len(all_lines) > lines else all_lines

            # For larger files, seek from the end
            with open(file_path, "rb") as f:
                # Start from the end and work backwards
                buffer_size = min(8192, file_size)
                f.seek(0, 2)  # Go to end of file
                file_length = f.tell()

                result: list[str] = []
                remaining = file_length

                while remaining > 0 and len(result) < lines:
                    # Read a chunk from the end
                    chunk_size = min(buffer_size, remaining)
                    remaining -= chunk_size
                    f.seek(remaining)
                    chunk = f.read(chunk_size)

                    # Split into lines
                    chunk_lines = chunk.decode("utf-8", errors="ignore").splitlines()
                    result = chunk_lines + result

                    if len(result) >= lines:
                        return result[-lines:]

                return result

        except Exception as e:
            logger.error(f"Error tailing file {file_path}: {e}")
            return []

    @staticmethod
    def read_jsonl_events(
        file_path: Path, event_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Read and parse JSONL events from a file.

        Args:
            file_path: Path to the JSONL file
            event_types: Optional list of event types to filter

        Returns:
            List of parsed events
        """
        events: list[dict] = []

        if not file_path.exists():
            return events

        try:
            with open(file_path) as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        event = json.loads(line)

                        # Filter by event type if specified
                        if event_types:
                            event_type = event.get("event_type", "")
                            if not any(et in event_type for et in event_types):
                                continue

                        events.append(event)

                    except json.JSONDecodeError:
                        logger.debug(
                            f"Skipping malformed JSON in {file_path}:{line_num}"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Error parsing event in {file_path}:{line_num}: {e}"
                        )

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")

        return events

    @staticmethod
    def find_jsonl_files(base_path: Path, pattern: str = "**/*.jsonl") -> List[Path]:
        """Find all JSONL files matching a pattern.

        Args:
            base_path: Base directory to search from
            pattern: Glob pattern for matching files

        Returns:
            List of matching file paths
        """
        if not base_path.exists():
            return []

        return list(base_path.glob(pattern))
