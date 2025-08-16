"""DuckDB schema definitions leveraging advanced types.

This module maintains backward compatibility while delegating to schema_loader.
All SQL schemas are now stored in individual .sql files in the schemas/ directory.
"""

from .schema_loader import SchemaLoader


# Load all schemas as module-level constants for backward compatibility
def _load_schema(name: str) -> str:
    """Load a schema by name."""
    loader = SchemaLoader()
    try:
        return loader.load_schema(name)
    except FileNotFoundError:
        # Return empty string if schema file not found
        return ""


# Schema constants - loaded from files
CONVERSATION_TURNS_SCHEMA = _load_schema("conversation_turns")
EVENT_SCHEMA = _load_schema("events")
EXPERIMENTS_SCHEMA = _load_schema("experiments")
CONVERSATIONS_SCHEMA = _load_schema("conversations")
TURN_METRICS_SCHEMA = _load_schema("turn_metrics")
MESSAGES_SCHEMA = _load_schema("messages")
TOKEN_USAGE_SCHEMA = _load_schema("token_usage")
CONTEXT_TRUNCATIONS_SCHEMA = _load_schema("context_truncations")
MATERIALIZED_VIEWS = _load_schema("views")


def get_all_schemas():
    """Return all schemas in the correct order for creation."""
    return [
        EXPERIMENTS_SCHEMA,
        CONVERSATIONS_SCHEMA,
        CONVERSATION_TURNS_SCHEMA,
        EVENT_SCHEMA,
        TURN_METRICS_SCHEMA,
        MESSAGES_SCHEMA,
        TOKEN_USAGE_SCHEMA,
        CONTEXT_TRUNCATIONS_SCHEMA,
        MATERIALIZED_VIEWS,
    ]
