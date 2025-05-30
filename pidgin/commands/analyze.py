"""Analyze experiment results."""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List
import json
from pathlib import Path

from pidgin.storage.experiments import ExperimentStorage
from pidgin.analysis.compression import CompressionAnalyzer
from pidgin.analysis.symbols import SymbolDetector
from pidgin.analysis.metrics import MetricsAnalyzer

app = typer.Typer()
console = Console()


@app.command()
def experiment(
    ctx: typer.Context,
    experiment_id: str = typer.Argument(..., help="Experiment ID to analyze"),
    compression: bool = typer.Option(True, "--compression/--no-compression", help="Analyze compression"),
    symbols: bool = typer.Option(True, "--symbols/--no-symbols", help="Analyze symbol emergence"),
    export: Optional[Path] = typer.Option(None, "--export", "-e", help="Export analysis to file"),
):
    """Analyze an experiment's results."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    # Load experiment
    experiment = storage.load(experiment_id)
    if not experiment:
        console.print(f"[red]Error: Experiment {experiment_id} not found[/red]")
        raise typer.Exit(1)
    
    if not experiment.conversation_history:
        console.print("[yellow]No conversation data to analyze[/yellow]")
        return
    
    console.print(Panel.fit(
        f"[bold blue]📊 Analyzing Experiment[/bold blue]\n\n{experiment.config.name}",
        border_style="blue"
    ))
    
    results = {}
    
    # Basic metrics
    metrics_analyzer = MetricsAnalyzer()
    basic_metrics = metrics_analyzer.analyze_experiment(experiment)
    _display_basic_metrics(basic_metrics)
    results["metrics"] = basic_metrics
    
    # Compression analysis
    if compression and experiment.config.compression_enabled:
        console.print("\n[bold]Compression Analysis:[/bold]")
        compression_analyzer = CompressionAnalyzer()
        compression_results = compression_analyzer.analyze_conversation(experiment.conversation_history)
        _display_compression_results(compression_results)
        results["compression"] = compression_results
    
    # Symbol analysis
    if symbols:
        console.print("\n[bold]Symbol Emergence:[/bold]")
        symbol_detector = SymbolDetector()
        symbol_results = symbol_detector.analyze_conversation(experiment.conversation_history)
        _display_symbol_results(symbol_results)
        results["symbols"] = symbol_results
    
    # Export if requested
    if export:
        export_data = {
            "experiment": experiment.to_dict(),
            "analysis": results,
        }
        
        with open(export, "w") as f:
            json.dump(export_data, f, indent=2)
        
        console.print(f"\n[green]✓ Analysis exported to {export}[/green]")


def _display_basic_metrics(metrics: dict):
    """Display basic experiment metrics."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("Total Turns", str(metrics["total_turns"]))
    table.add_row("Total Tokens", f"{metrics['total_tokens']:,}")
    table.add_row("Avg Tokens/Turn", f"{metrics['avg_tokens_per_turn']:.1f}")
    table.add_row("Avg Turn Length", f"{metrics['avg_turn_length']:.1f} chars")
    
    if metrics.get("duration"):
        table.add_row("Duration", f"{metrics['duration']:.1f}s")
        table.add_row("Avg Turn Time", f"{metrics['avg_turn_time']:.1f}s")
    
    console.print(table)


def _display_compression_results(results: dict):
    """Display compression analysis results."""
    if "progression" in results:
        # Show compression over time
        table = Table(title="Compression Progression", show_header=True)
        table.add_column("Phase", style="cyan")
        table.add_column("Turns", justify="center")
        table.add_column("Avg Length", justify="right")
        table.add_column("Compression", justify="right")
        
        for phase in results["progression"]:
            table.add_row(
                phase["name"],
                f"{phase['start']}-{phase['end']}",
                f"{phase['avg_length']:.0f}",
                f"{phase['compression']:.1%}"
            )
        
        console.print(table)
    
    if "symbols" in results:
        console.print(f"\nUnique symbols detected: {len(results['symbols'])}")
        if results['symbols']:
            console.print(f"Examples: {', '.join(list(results['symbols'])[:10])}")


def _display_symbol_results(results: dict):
    """Display symbol analysis results."""
    if not results.get("symbols"):
        console.print("[dim]No significant symbols detected[/dim]")
        return
    
    table = Table(title="Symbol Analysis", show_header=True)
    table.add_column("Symbol", style="cyan")
    table.add_column("First Seen", justify="center")
    table.add_column("Frequency", justify="right")
    table.add_column("Stability", justify="right")
    
    # Sort by frequency
    symbols = sorted(
        results["symbols"].items(),
        key=lambda x: x[1]["frequency"],
        reverse=True
    )[:10]  # Top 10
    
    for symbol, data in symbols:
        table.add_row(
            symbol,
            f"Turn {data['first_seen']}",
            str(data['frequency']),
            f"{data['stability']:.1%}"
        )
    
    console.print(table)
    
    if "emergence_pattern" in results:
        console.print(f"\nEmergence pattern: {results['emergence_pattern']}")


@app.command()
def compare(
    ctx: typer.Context,
    experiments: List[str] = typer.Argument(..., help="Experiment IDs to compare"),
    metric: str = typer.Option("compression", "--metric", "-m", help="Metric to compare"),
):
    """Compare multiple experiments."""
    console.print("[yellow]Compare command not yet implemented[/yellow]")
    # TODO: Implement comparison