# pidgin/cli/branch.py
"""Branch command for forking conversations from any point."""

from pathlib import Path
from typing import Optional

import rich_click as click
import yaml
from rich.console import Console

from ..io.paths import get_experiments_dir
from ..ui.display_utils import DisplayUtils
from . import ORIGINAL_CWD
from .branch_handlers import (
    BranchConfigBuilder,
    BranchExecutor,
    BranchSourceFinder,
    BranchSpecWriter,
)
from .error_handler import CLIErrorHandler, ValidationError
from .error_handler import FileNotFoundError as CLIFileNotFoundError
from .name_generator import generate_experiment_name

console = Console()
display = DisplayUtils(console)
error_handler = CLIErrorHandler(console)


@click.command()
@click.argument("conversation_id", required=True)
@click.option(
    "--turn", "-t", type=int, help="Turn number to branch from (default: last turn)"
)
@click.option("--agent-a", "-a", help="Override agent A model")
@click.option("--agent-b", "-b", help="Override agent B model")
@click.option("--temperature", type=float, help="Override temperature for both agents")
@click.option("--temp-a", type=float, help="Override temperature for agent A")
@click.option("--temp-b", type=float, help="Override temperature for agent B")
@click.option("--awareness", "-w", help="Override awareness level or YAML file")
@click.option("--awareness-a", help="Override awareness for agent A")
@click.option("--awareness-b", help="Override awareness for agent B")
@click.option("--max-turns", type=int, help="Override maximum turns")
@click.option("--name", "-n", help="Name for the branched experiment")
@click.option(
    "--repetitions",
    "-r",
    type=int,
    default=1,
    help="Number of branches to create (default: 1)",
)
@click.option("--quiet", "-q", is_flag=True, help="Run in background")
@click.option(
    "--spec", "-s", type=click.Path(), help="Save branch configuration as YAML spec"
)
def branch(
    conversation_id: str,
    turn: Optional[int],
    agent_a: Optional[str],
    agent_b: Optional[str],
    temperature: Optional[float],
    temp_a: Optional[float],
    temp_b: Optional[float],
    awareness: Optional[str],
    awareness_a: Optional[str],
    awareness_b: Optional[str],
    max_turns: Optional[int],
    name: Optional[str],
    repetitions: int,
    quiet: bool,
    spec: Optional[str],
):
    """Branch a conversation from any point with parameter changes.

    This command allows you to fork an existing conversation from a
    specific turn and continue with different parameters.

    [bold]EXAMPLES:[/bold]

    [#4c566a]Branch from last turn:[/#4c566a]
      pidgin branch conv_exp_abc123

    [#4c566a]Branch from turn 10:[/#4c566a]
      pidgin branch conv_exp_abc123 --turn 10

    [#4c566a]Change models:[/#4c566a]
      pidgin branch conv_exp_abc123 -a gpt-4 -b claude

    [#4c566a]Change temperature:[/#4c566a]
      pidgin branch conv_exp_abc123 --temp-a 1.5

    [#4c566a]Multiple branches:[/#4c566a]
      pidgin branch conv_exp_abc123 -r 5 --temperature 1.2

    [#4c566a]Save as spec:[/#4c566a]
      pidgin branch conv_exp_abc123 --spec branch_spec.yaml
    """
    # 1. Find source conversation
    finder = BranchSourceFinder()
    exp_dir = get_experiments_dir()
    source = finder.find_conversation(exp_dir, conversation_id, turn)
    if not source:
        display.error(
            f"Conversation '{conversation_id}' not found",
            context="Check the conversation ID and try again",
        )
        return

    # 2. Display source info
    display.info(source.get_info(), title="◆ Branch Source", use_panel=True)

    # 3. Build configuration
    builder = BranchConfigBuilder(source.config)

    # Apply overrides
    if errors := builder.apply_model_overrides(agent_a, agent_b):
        for error in errors:
            display.error(error)
        return

    builder.apply_temperature_overrides(temperature, temp_a, temp_b)
    builder.apply_awareness_overrides(awareness, awareness_a, awareness_b)
    builder.apply_other_overrides(max_turns)

    # 4. Generate name if needed
    if not name:
        name = f"{generate_experiment_name()}_branch"
        display.dim(f"Generated branch name: {name}")

    # 5. Save spec if requested
    if spec:
        writer = BranchSpecWriter()
        if error := writer.save_spec(
            spec,
            builder.branch_config,
            source.metadata,
            source.messages,
            name,
            repetitions,
            conversation_id,
            source.branch_point,
        ):
            display.error(f"Failed to save spec: {error}")
            return
        display.info(f"Saved branch spec to: {spec}")

    # 6. Show changes
    if changes := builder.get_changes():
        display.info("\n".join(changes), title="◆ Branch Changes", use_panel=True)
    else:
        display.info("No parameter changes (exact replay)", use_panel=False)

    # 7. Build experiment config
    config = builder.build_experiment_config(
        name, repetitions, source.messages, conversation_id, source.branch_point
    )

    # 8. Execute
    executor = BranchExecutor(display, console)
    executor.execute(config, quiet, ORIGINAL_CWD)


def branch_from_spec(spec_file: str):
    """Run a branch from a YAML specification.

    This allows replaying branches with saved configurations.
    """
    try:
        with open(spec_file) as f:
            spec = yaml.safe_load(f)

        # Extract branch metadata
        branch_info = spec.get("branch_from", {})
        conversation_id = branch_info.get("conversation_id")
        turn = branch_info.get("turn")

        if not conversation_id:
            display.error("Invalid branch spec: missing conversation_id")
            return

        # Build command arguments
        args = ["branch", conversation_id]

        if turn:
            args.extend(["--turn", str(turn)])

        # Add model overrides
        if "agent_a_model" in spec:
            args.extend(["--agent-a", spec["agent_a_model"]])
        if "agent_b_model" in spec:
            args.extend(["--agent-b", spec["agent_b_model"]])

        # Add other parameters
        if "name" in spec:
            args.extend(["--name", spec["name"]])
        if "repetitions" in spec:
            args.extend(["--repetitions", str(spec["repetitions"])])

        # Execute branch command
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(branch, args)

        if result.exit_code != 0:
            display.error(f"Branch failed: {result.output}")

    except yaml.YAMLError as e:
        raise ValidationError(
            f"Invalid YAML in spec file: {e}",
            suggestion="Check YAML syntax with a validator",
        )
    except FileNotFoundError:
        raise CLIFileNotFoundError(
            Path(spec_file), suggestion="Verify the spec file path is correct"
        )
    except (PermissionError, OSError) as e:
        display.error(f"Failed to load branch spec: {e}")
