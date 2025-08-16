"""Base deserializer with shared utilities."""

from datetime import datetime
from typing import Any, Dict


class BaseDeserializer:
    """Base deserializer with shared utilities."""

    @staticmethod
    def parse_timestamp(timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Parsed datetime object
        """
        # Handle multiple timestamp formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",  # With microseconds
            "%Y-%m-%dT%H:%M:%S",  # Without microseconds
            "%Y-%m-%d %H:%M:%S.%f",  # Space separator with microseconds
            "%Y-%m-%d %H:%M:%S",  # Space separator without microseconds
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # If none match, try fromisoformat as fallback
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    @staticmethod
    def get_or_default(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get value from dict with default.

        Args:
            data: Dictionary to get value from
            key: Key to look up
            default: Default value if key not found

        Returns:
            Value from dict or default
        """
        return data.get(key, default)
