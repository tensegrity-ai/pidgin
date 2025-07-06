# pidgin/cli/import_cmd.py
"""Import JSONL experiments into DuckDB for analysis."""

import asyncio
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from ..io.paths import get_experiments_dir, get_database_path
from ..database.batch_importer import BatchImporter
from ..database.transcript_generator import TranscriptGenerator
from ..io.logger import get_logger
from .constants import NORD_GREEN, NORD_RED, NORD_YELLOW, NORD_CYAN

console = Console()
logger = get_logger("import_cmd")


@click.command(name="import")
@click.argument("experiment_id", required=False)
@click.option("--all", is_flag=True, help="Import all unimported experiments")
@click.option("--force", is_flag=True, help="Force reimport even if already imported")
@click.option("--transcripts", is_flag=True, help="Generate markdown transcripts after import")
@click.option("--db-path", type=click.Path(path_type=Path), help="Path to DuckDB database (default: ~/.pidgin/pidgin.db)")
def import_cmd(experiment_id: str, all: bool, force: bool, transcripts: bool, db_path: Path):
    """Import JSONL experiments into DuckDB for analysis.
    
    This command batch imports completed experiments from their JSONL files
    into DuckDB for efficient querying and analysis.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Import specific experiment:[/#4c566a]
        pidgin import exp_abc123
    
    [#4c566a]Import all unimported experiments:[/#4c566a]
        pidgin import --all
    
    [#4c566a]Force reimport:[/#4c566a]
        pidgin import exp_abc123 --force
    
    [#4c566a]Import with transcript generation:[/#4c566a]
        pidgin import exp_abc123 --transcripts
    """
    # Validate arguments
    if not experiment_id and not all:
        console.print(f"[{NORD_RED}]Error: Specify an experiment ID or use --all[/{NORD_RED}]")
        raise click.Abort()
    
    if experiment_id and all:
        console.print(f"[{NORD_RED}]Error: Cannot specify both experiment ID and --all[/{NORD_RED}]")
        raise click.Abort()
    
    # Get paths
    exp_base = get_experiments_dir()
    if not db_path:
        db_path = get_database_path()
    
    # Create importer
    importer = BatchImporter(db_path)
    
    # Run import
    asyncio.run(_run_import(importer, exp_base, experiment_id, all, force, transcripts, db_path))


async def _run_import(importer: BatchImporter, exp_base: Path, experiment_id: str, 
                     import_all: bool, force: bool, generate_transcripts: bool, db_path: Path):
    """Run the import operation."""
    
    if import_all:
        # Import all unimported experiments
        console.print(f"[{NORD_CYAN}]Scanning for unimported experiments...[/{NORD_CYAN}]")
        
        # Get all experiment directories
        exp_dirs = []
        for exp_dir in sorted(exp_base.glob("exp_*")):
            if not exp_dir.is_dir():
                continue
            
            # Check if already imported
            if not force and (exp_dir / ".imported").exists():
                continue
                
            exp_dirs.append(exp_dir)
        
        if not exp_dirs:
            console.print(f"[{NORD_YELLOW}]No unimported experiments found[/{NORD_YELLOW}]")
            return
        
        console.print(f"[{NORD_GREEN}]Found {len(exp_dirs)} experiments to import[/{NORD_GREEN}]")
        
        # Import with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Importing experiments...", total=len(exp_dirs))
            
            results = []
            exp_dirs_map = {}  # Map experiment_id to exp_dir
            
            for exp_dir in exp_dirs:
                result = importer.import_experiment(exp_dir, force=force)
                results.append(result)
                if result.success:
                    exp_dirs_map[result.experiment_id] = exp_dir
                progress.update(task, advance=1, 
                              description=f"Importing {exp_dir.name}...")
        
        # Show results summary
        _show_results_summary(results)
        
        # Generate transcripts for successful imports if requested
        if generate_transcripts:
            successful_results = [r for r in results if r.success]
            if successful_results:
                console.print(f"\n[{NORD_CYAN}]Generating transcripts for {len(successful_results)} experiments...[/{NORD_CYAN}]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console
                ) as progress:
                    task = progress.add_task("Generating transcripts...", total=len(successful_results))
                    
                    with TranscriptGenerator(db_path) as generator:
                        for result in successful_results:
                            exp_dir = exp_dirs_map[result.experiment_id]
                            generator.generate_experiment_transcripts(result.experiment_id, exp_dir)
                            progress.update(task, advance=1,
                                          description=f"Generating for {result.experiment_id[:20]}...")
                
                console.print(f"[{NORD_GREEN}][OK] All transcripts generated[/{NORD_GREEN}]")
        
    else:
        # Import specific experiment
        # Handle partial ID match
        matching_dirs = list(exp_base.glob(f"{experiment_id}*"))
        if not matching_dirs:
            console.print(f"[{NORD_RED}]No experiment found matching '{experiment_id}'[/{NORD_RED}]")
            return
        
        if len(matching_dirs) > 1:
            console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}':[/{NORD_RED}]")
            for d in matching_dirs:
                console.print(f"  • {d.name}")
            return
        
        exp_dir = matching_dirs[0]
        
        # Check if already imported
        if not force and (exp_dir / ".imported").exists():
            console.print(f"[{NORD_YELLOW}]Experiment {exp_dir.name} already imported[/{NORD_YELLOW}]")
            console.print(f"Use --force to reimport")
            return
        
        console.print(f"[{NORD_CYAN}]Importing {exp_dir.name}...[/{NORD_CYAN}]")
        
        # Import with spinner
        with console.status(f"Importing {exp_dir.name}..."):
            result = importer.import_experiment(exp_dir, force=force)
        
        # Show result
        if result.success:
            console.print(f"[{NORD_GREEN}][OK] Successfully imported {result.experiment_id}[/{NORD_GREEN}]")
            console.print(f"  • Events: {result.events_imported}")
            console.print(f"  • Conversations: {result.conversations_imported}")
            console.print(f"  • Duration: {result.duration_seconds:.1f}s")
            
            # Generate transcripts if requested
            if generate_transcripts:
                console.print(f"[{NORD_CYAN}]Generating transcripts...[/{NORD_CYAN}]")
                with TranscriptGenerator(db_path) as generator:
                    generator.generate_experiment_transcripts(result.experiment_id, exp_dir)
                console.print(f"[{NORD_GREEN}][OK] Transcripts generated[/{NORD_GREEN}]")
        else:
            console.print(f"[{NORD_RED}][FAIL] Failed to import {result.experiment_id}[/{NORD_RED}]")
            console.print(f"  Error: {result.error}")


def _show_results_summary(results):
    """Show summary of import results."""
    # Count successes and failures
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    
    # Create summary table
    table = Table(show_header=True, header_style=f"bold {NORD_CYAN}")
    table.add_column("Experiment", style=NORD_CYAN)
    table.add_column("Status", style=NORD_GREEN)
    table.add_column("Events", justify="right")
    table.add_column("Conversations", justify="right")
    table.add_column("Duration", justify="right")
    
    total_events = 0
    total_convs = 0
    total_duration = 0
    
    for result in results:
        status = f"[{NORD_GREEN}][OK][/{NORD_GREEN}]" if result.success else f"[{NORD_RED}][FAIL][/{NORD_RED}]"
        
        table.add_row(
            result.experiment_id[:20],
            status,
            str(result.events_imported) if result.success else "-",
            str(result.conversations_imported) if result.success else "-",
            f"{result.duration_seconds:.1f}s"
        )
        
        if result.success:
            total_events += result.events_imported
            total_convs += result.conversations_imported
            total_duration += result.duration_seconds
    
    console.print("\n", table, "\n")
    
    # Summary
    console.print(f"[bold {NORD_GREEN}]Import Summary:[/bold {NORD_GREEN}]")
    console.print(f"  • Successful: {len(successes)}")
    console.print(f"  • Failed: {len(failures)}")
    console.print(f"  • Total events: {total_events:,}")
    console.print(f"  • Total conversations: {total_convs}")
    console.print(f"  • Total duration: {total_duration:.1f}s")
    
    # Show failures if any
    if failures:
        console.print(f"\n[{NORD_RED}]Failed imports:[/{NORD_RED}]")
        for result in failures:
            console.print(f"  • {result.experiment_id}: {result.error}")