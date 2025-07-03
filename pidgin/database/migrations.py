"""Database migration utilities for DuckDB schema evolution."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from .async_duckdb import AsyncDuckDB
from .schema import get_all_schemas, get_drop_all_sql
from ..io.logger import get_logger

logger = get_logger("migrations")


class MigrationRunner:
    """Handles database migrations for DuckDB schema."""
    
    def __init__(self, db_path: Path):
        """Initialize migration runner.
        
        Args:
            db_path: Path to DuckDB database
        """
        self.db_path = db_path
        self.db = AsyncDuckDB(db_path)
    
    async def create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT now(),
                execution_time_ms INTEGER
            )
        """)
    
    async def get_current_version(self) -> int:
        """Get current schema version."""
        result = await self.db.fetch_one(
            "SELECT MAX(version) as version FROM schema_migrations"
        )
        return result['version'] if result and result['version'] else 0
    
    async def apply_migration(self, version: int, name: str, sql: str):
        """Apply a single migration."""
        start_time = datetime.now()
        
        try:
            # Execute migration SQL
            await self.db.execute(sql)
            
            # Record migration
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            await self.db.execute(
                "INSERT INTO schema_migrations (version, name, execution_time_ms) VALUES (?, ?, ?)",
                (version, name, execution_time_ms)
            )
            
            logger.info(f"Applied migration {version}: {name} ({execution_time_ms}ms)")
            
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {name} - {e}")
            raise
    
    async def migrate_to_event_sourcing(self):
        """Migrate from current schema to event-sourced schema."""
        logger.info("Starting migration to event-sourced DuckDB schema")
        
        # Create migrations table
        await self.create_migrations_table()
        
        current_version = await self.get_current_version()
        logger.info(f"Current schema version: {current_version}")
        
        # Define migrations
        migrations = [
            (1, "create_event_sourcing_schema", await self._get_event_sourcing_migration()),
            (2, "migrate_existing_data", await self._get_data_migration()),
            (3, "create_materialized_views", await self._get_views_migration()),
        ]
        
        # Apply migrations in order
        for version, name, sql in migrations:
            if version > current_version:
                await self.apply_migration(version, name, sql)
        
        logger.info("Migration completed successfully")
    
    async def _get_event_sourcing_migration(self) -> str:
        """Get SQL for creating event sourcing schema."""
        # Combine all schema definitions
        schemas = get_all_schemas()
        return "\n\n".join(schemas)
    
    async def _get_data_migration(self) -> str:
        """Get SQL for migrating existing data to new schema."""
        # Check if old tables exist
        old_tables = await self.db.fetch_all("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_name IN ('experiments', 'conversations', 'turn_metrics', 
                              'message_metrics', 'word_frequencies')
        """)
        
        if not old_tables:
            return "-- No existing data to migrate"
        
        migration_sql = []
        
        # Check which old tables exist
        table_names = {row['table_name'] for row in old_tables}
        
        # Migrate experiments if exists
        if 'experiments' in table_names:
            # Check if it's the old schema (has config as JSON)
            old_schema = await self.db.fetch_one("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'experiments' 
                AND column_name = 'config' 
                AND data_type = 'JSON'
            """)
            
            if old_schema:
                migration_sql.append("""
                -- Backup old experiments table
                CREATE TABLE experiments_old AS SELECT * FROM experiments;
                
                -- Drop and recreate with new schema
                DROP TABLE experiments CASCADE;
                """)
                
                # Add new schema creation
                migration_sql.append(self._get_experiments_schema())
                
                # Migrate data
                migration_sql.append("""
                -- Migrate experiments data
                INSERT INTO experiments (
                    experiment_id, name, created_at, started_at, completed_at, status,
                    config, progress, metadata
                )
                SELECT 
                    experiment_id,
                    name,
                    created_at,
                    started_at,
                    completed_at,
                    status,
                    -- Convert JSON config to STRUCT
                    STRUCT(
                        CAST(config->>'$.repetitions' AS INTEGER) as repetitions,
                        CAST(config->>'$.max_turns' AS INTEGER) as max_turns,
                        config->>'$.initial_prompt' as initial_prompt,
                        CAST(config->>'$.convergence_threshold' AS DOUBLE) as convergence_threshold,
                        CAST(config->>'$.temperature_a' AS DOUBLE) as temperature_a,
                        CAST(config->>'$.temperature_b' AS DOUBLE) as temperature_b
                    ) as config,
                    -- Progress struct
                    STRUCT(
                        total_conversations,
                        completed_conversations,
                        failed_conversations
                    ) as progress,
                    metadata
                FROM experiments_old;
                """)
        
        # Similar migrations for other tables...
        # (Keeping this focused on the pattern - would implement full migrations for all tables)
        
        return "\n\n".join(migration_sql) if migration_sql else "-- No migration needed"
    
    async def _get_views_migration(self) -> str:
        """Get SQL for creating materialized views."""
        # For now, return empty as DuckDB CE doesn't support materialized views
        # We use regular views instead
        return "-- Views created in schema definition"
    
    def _get_experiments_schema(self) -> str:
        """Get experiments schema definition."""
        from .schema import EXPERIMENTS_SCHEMA
        return EXPERIMENTS_SCHEMA
    
    async def create_event_from_old_format(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert old format data to event format."""
        return {
            'event_type': event_type,
            'conversation_id': data.get('conversation_id'),
            'experiment_id': data.get('experiment_id'),
            'event_data': json.dumps(data),
            'timestamp': data.get('timestamp', datetime.now())
        }
    
    async def close(self):
        """Close database connection."""
        await self.db.close()


async def migrate_database(db_path: Path):
    """Run database migrations.
    
    Args:
        db_path: Path to DuckDB database
    """
    runner = MigrationRunner(db_path)
    try:
        await runner.migrate_to_event_sourcing()
    finally:
        await runner.close()


async def create_fresh_database(db_path: Path):
    """Create a fresh database with the new schema.
    
    Args:
        db_path: Path to DuckDB database
    """
    db = AsyncDuckDB(db_path)
    try:
        # Create migrations table first
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT now(),
                execution_time_ms INTEGER
            )
        """)
        
        # Create all schemas
        for schema_sql in get_all_schemas():
            await db.execute(schema_sql)
        
        # Mark as fresh install
        await db.execute("""
            INSERT INTO schema_migrations (version, name, execution_time_ms)
            VALUES (1, 'initial_schema', 0)
        """)
        
        logger.info(f"Created fresh database at {db_path}")
    finally:
        await db.close()


async def reset_database(db_path: Path):
    """Reset database to fresh state (WARNING: destroys all data).
    
    Args:
        db_path: Path to DuckDB database
    """
    db = AsyncDuckDB(db_path)
    try:
        # Drop everything
        await db.execute(get_drop_all_sql())
        
        # Recreate
        await create_fresh_database(db_path)
        
        logger.info(f"Reset database at {db_path}")
    finally:
        await db.close()