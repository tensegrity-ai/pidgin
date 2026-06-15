# pidgin/cli/import_data.py
"""Re-import experiments from JSONL into the analysis database."""

import rich_click as click
from rich.console import Console

from ..database.event_store import EventStore
from ..database.transcript_generator import TranscriptGenerator
from ..io.paths import get_database_path, get_experiments_dir
from ..ui.display_utils import DisplayUtils

console = Console()
display = DisplayUtils(console)


@click.command(name="import")
@click.argument("experiment_id", required=False)
@click.option(
    "--all",
    "import_all",
    is_flag=True,
    help="Re-import every experiment found in the output directory",
)
@click.option(
    "--no-transcripts",
    is_flag=True,
    help="Skip regenerating transcripts after import",
)
def import_data(experiment_id, import_all, no_transcripts):
    """Re-import experiments from their JSONL files into the database.

    JSONL files are the source of truth, so this rebuilds the DuckDB tables and
    transcripts from them. Use it after upgrading to pick up fixes, or to heal
    a database with stale or partial data. Existing rows for each experiment are
    cleared first, so re-running is safe (no duplicates).

    Pass an experiment id or name to re-import just one, or --all for every
    experiment in the output directory.
    """
    experiments_dir = get_experiments_dir()
    if not experiments_dir.exists():
        display.error(f"No experiments directory found at {experiments_dir}")
        return

    # Resolve which experiment directories to process
    candidates = [
        d
        for d in sorted(experiments_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".") and (d / "manifest.json").exists()
    ]

    if not import_all:
        if not experiment_id:
            display.error("Specify an experiment id/name, or use --all.")
            return
        candidates = [
            d
            for d in candidates
            if d.name == experiment_id or d.name.startswith(experiment_id)
        ]
        if not candidates:
            display.error(f"No experiment matching '{experiment_id}' found.")
            return

    db_path = get_database_path()
    succeeded, failed = 0, 0

    with EventStore(db_path) as event_store:
        for exp_dir in candidates:
            result = event_store.reimport_experiment(exp_dir)
            if not result.success:
                failed += 1
                display.error(f"{exp_dir.name}: {result.error}")
                continue

            succeeded += 1
            if not no_transcripts:
                try:
                    TranscriptGenerator(event_store).generate_experiment_transcripts(
                        result.experiment_id, exp_dir
                    )
                except Exception as e:  # transcripts are best-effort
                    display.warning(f"{exp_dir.name}: transcripts failed ({e})")

            display.dim(
                f"{exp_dir.name}: {result.turns_imported} turns, "
                f"{result.conversations_imported} conversations"
            )

    display.info(
        f"Re-imported {succeeded} experiment(s)"
        + (f", {failed} failed" if failed else ""),
        use_panel=False,
    )
