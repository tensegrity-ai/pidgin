"""Database migration CLI commands."""

import asyncio
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.prompt import Confirm

from ..database.migrations import migrate_database, create_fresh_database, reset_database
from ..database.async_duckdb import AsyncDuckDB
from ..io.logger import get_logger

console = Console()
logger = get_logger("migrate")


@click.group(name="db")
def db_cli():
    """Database management commands."""
    pass


@db_cli.command()
@click.option('--db-path', type=click.Path(), 
              default='pidgin_output/experiments/experiments.duckdb',
              help='Path to DuckDB database')
@click.option('--fresh', is_flag=True, help='Create fresh database (no migration)')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
def migrate(db_path: str, fresh: bool, force: bool):
    """Migrate database to new DuckDB schema with advanced features.
    
    This command will:
    - Convert existing SQLite-style schema to DuckDB native types
    - Enable event sourcing architecture
    - Create optimized views for analytics
    - Preserve all existing data
    """
    db_path = Path(db_path).resolve()
    
    if fresh:
        if not force and db_path.exists():
            if not Confirm.ask(f"[yellow]Database exists at {db_path}. Create fresh database?[/yellow]"):
                console.print("[red]Migration cancelled[/red]")
                return
        
        console.print(f"\n[bold cyan]Creating fresh database at {db_path}[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating database schema...", total=None)
            
            async def create():
                await create_fresh_database(db_path)
            
            asyncio.run(create())
            progress.update(task, completed=True)
        
        console.print("\n[bold green]✓ Fresh database created successfully![/bold green]")
        return
    
    # Regular migration
    if not db_path.exists():
        console.print(f"[yellow]Database not found at {db_path}[/yellow]")
        if Confirm.ask("Create new database?"):
            asyncio.run(create_fresh_database(db_path))
            console.print("[bold green]✓ New database created![/bold green]")
        return
    
    console.print(Panel.fit(
        "[bold cyan]DuckDB Migration[/bold cyan]\n\n"
        "This will migrate your database to use:\n"
        "• Event sourcing architecture\n"
        "• Native DuckDB types (MAP, STRUCT)\n"
        "• Optimized analytics views\n"
        "• Async operations throughout\n\n"
        "[yellow]Your data will be preserved![/yellow]",
        title="Migration Info"
    ))
    
    if not force:
        if not Confirm.ask("\n[bold]Proceed with migration?[/bold]"):
            console.print("[red]Migration cancelled[/red]")
            return
    
    console.print("\n[bold cyan]Starting migration...[/bold cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running migration...", total=None)
        
        async def run_migration():
            try:
                await migrate_database(db_path)
            except Exception as e:
                logger.error(f"Migration failed: {e}", exc_info=True)
                raise
        
        try:
            asyncio.run(run_migration())
            progress.update(task, completed=True)
            console.print("\n[bold green]✓ Migration completed successfully![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]✗ Migration failed: {e}[/bold red]")
            raise click.ClickException(str(e))


@db_cli.command()
@click.option('--db-path', type=click.Path(), 
              default='pidgin_output/experiments/experiments.duckdb',
              help='Path to DuckDB database')
def status(db_path: str):
    """Check database status and schema version."""
    db_path = Path(db_path).resolve()
    
    if not db_path.exists():
        console.print(f"[red]Database not found at {db_path}[/red]")
        return
    
    async def check_status():
        db = AsyncDuckDB(db_path)
        try:
            # Check if migrations table exists
            result = await db.fetch_one("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_name = 'schema_migrations'
            """)
            
            if result['count'] == 0:
                console.print("[yellow]Database uses old schema (no migrations table)[/yellow]")
                return
            
            # Get current version
            version_result = await db.fetch_one(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            current_version = version_result['version'] if version_result['version'] else 0
            
            # Get migration history
            migrations = await db.fetch_all(
                "SELECT * FROM schema_migrations ORDER BY version"
            )
            
            console.print(f"\n[bold]Database: {db_path}[/bold]")
            console.print(f"Schema version: [cyan]{current_version}[/cyan]\n")
            
            if migrations:
                console.print("[bold]Migration History:[/bold]")
                for m in migrations:
                    console.print(
                        f"  v{m['version']}: {m['name']} "
                        f"([dim]{m['applied_at']}[/dim], {m['execution_time_ms']}ms)"
                    )
            
            # Check for new schema features
            console.print("\n[bold]Schema Features:[/bold]")
            
            # Check for events table
            events_result = await db.fetch_one("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_name = 'events'
            """)
            if events_result['count'] > 0:
                event_count = await db.fetch_one("SELECT COUNT(*) as count FROM events")
                console.print(f"  ✓ Event sourcing enabled ({event_count['count']} events)")
            else:
                console.print("  ✗ Event sourcing not enabled")
            
            # Check for native types
            tm_result = await db.fetch_one("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'turn_metrics' 
                AND column_name = 'vocabulary'
            """)
            if tm_result and 'STRUCT' in tm_result['data_type']:
                console.print("  ✓ Native DuckDB types (STRUCT, MAP)")
            else:
                console.print("  ✗ Using legacy column storage")
            
            # Check for views
            views_result = await db.fetch_all("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_type = 'VIEW'
                AND table_name IN ('experiment_dashboard', 'convergence_trends')
            """)
            if views_result:
                console.print(f"  ✓ Analytics views ({len(views_result)} views)")
            else:
                console.print("  ✗ No analytics views")
            
        finally:
            await db.close()
    
    asyncio.run(check_status())


@db_cli.command()
@click.option('--db-path', type=click.Path(), 
              default='pidgin_output/experiments/experiments.duckdb',
              help='Path to DuckDB database')
@click.option('--force', is_flag=True, help='Skip confirmation')
def reset(db_path: str, force: bool):
    """Reset database to fresh state (WARNING: destroys all data)."""
    db_path = Path(db_path).resolve()
    
    if not db_path.exists():
        console.print(f"[red]Database not found at {db_path}[/red]")
        return
    
    console.print(Panel.fit(
        "[bold red]WARNING: This will DELETE ALL DATA![/bold red]\n\n"
        "This command will:\n"
        "• Drop all tables and views\n"
        "• Delete all experiments and conversations\n"
        "• Create fresh schema\n\n"
        "[bold red]This cannot be undone![/bold red]",
        title="Reset Database",
        border_style="red"
    ))
    
    if not force:
        if not Confirm.ask("\n[bold red]Are you SURE you want to reset the database?[/bold red]"):
            console.print("[green]Reset cancelled[/green]")
            return
        
        # Double confirmation
        if not Confirm.ask("[bold red]Really sure? Type 'yes' to confirm[/bold red]"):
            console.print("[green]Reset cancelled[/green]")
            return
    
    console.print("\n[bold red]Resetting database...[/bold red]")
    
    async def run_reset():
        await reset_database(db_path)
    
    try:
        asyncio.run(run_reset())
        console.print("\n[bold green]✓ Database reset complete![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]✗ Reset failed: {e}[/bold red]")
        raise click.ClickException(str(e))


# Register with main CLI
def register_commands(cli):
    """Register database commands with main CLI."""
    cli.add_command(db_cli)