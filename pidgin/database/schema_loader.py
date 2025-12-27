"""Schema loader for DuckDB database schemas."""

from pathlib import Path
from typing import List


class SchemaLoader:
    """Load SQL schemas from files."""

    def __init__(self):
        self.schemas_dir = Path(__file__).parent / "schemas"

    def load_schema(self, name: str) -> str:
        """Load a schema by name.

        Args:
            name: Schema name (without .sql extension)

        Returns:
            SQL schema content

        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        schema_path = self.schemas_dir / f"{name}.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path) as f:
            return f.read()

    def get_all_schemas(self) -> List[str]:
        """Get all schema definitions in order.

        Returns:
            List of SQL schema strings
        """
        # Order matters for dependencies
        schema_order = [
            "events",
            "experiments",
            "conversations",
            "turn_metrics",
            "conversation_turns",  # Wide-table schema
            "messages",
            "thinking_traces",  # Extended thinking/reasoning traces
            "token_usage",
            "context_truncations",
            # Views are optional and created separately
        ]

        schemas = []
        for name in schema_order:
            try:
                schemas.append(self.load_schema(name))
            except FileNotFoundError:
                # Skip missing schemas
                pass

        return schemas

    def get_drop_all_sql(self) -> str:
        """Get SQL to drop all tables (for clean migrations).

        Returns:
            SQL to drop all tables and views
        """
        return """
        DROP VIEW IF EXISTS vocabulary_analysis CASCADE;
        DROP VIEW IF EXISTS convergence_trends CASCADE;
        DROP VIEW IF EXISTS experiment_dashboard CASCADE;
        DROP TABLE IF EXISTS context_truncations CASCADE;
        DROP TABLE IF EXISTS token_usage CASCADE;
        DROP TABLE IF EXISTS thinking_traces CASCADE;
        DROP TABLE IF EXISTS messages CASCADE;
        DROP TABLE IF EXISTS turn_metrics CASCADE;
        DROP TABLE IF EXISTS conversation_turns CASCADE;
        DROP TABLE IF EXISTS conversations CASCADE;
        DROP TABLE IF EXISTS experiments CASCADE;
        DROP TABLE IF EXISTS events CASCADE;
        """

    def get_views_sql(self) -> str:
        """Get SQL for creating views.

        Returns:
            SQL for creating views, or empty string if not found
        """
        try:
            return self.load_schema("views")
        except FileNotFoundError:
            return ""


# Module-level convenience functions - create new instance each time
def get_all_schemas() -> List[str]:
    """Get all schema definitions in order."""
    loader = SchemaLoader()
    return loader.get_all_schemas()


def get_drop_all_sql() -> str:
    """Get SQL to drop all tables (for clean migrations)."""
    loader = SchemaLoader()
    return loader.get_drop_all_sql()
