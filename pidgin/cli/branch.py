# pidgin/cli/branch.py
"""Branch command for forking conversations from any point."""

import asyncio
import json
from typing import Optional

import rich_click as click
import yaml
from rich.console import Console

from ..experiments import ExperimentConfig, ExperimentManager
from ..experiments.state_builder import get_state_builder
from ..io.paths import get_experiments_dir
from ..ui.display_utils import DisplayUtils
from . import ORIGINAL_CWD
from .helpers import validate_model_id
from .name_generator import generate_experiment_name

console = Console()
display = DisplayUtils(console)


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
    # Find the conversation
    experiments_dir = get_experiments_dir()
    state_builder = get_state_builder()

    # Search for the conversation across all experiments
    conversation_state = None
    source_exp_dir = None

    for exp_dir in experiments_dir.glob("exp_*"):
        if not exp_dir.is_dir():
            continue

        # Try to extract state
        state = state_builder.get_conversation_state(exp_dir, conversation_id, turn)
        if state:
            conversation_state = state
            source_exp_dir = exp_dir
            break

    if not conversation_state:
        display.error(
            f"Conversation '{conversation_id}' not found",
            context="Check the conversation ID and try again",
        )
        return

    # Extract original configuration
    original_config = conversation_state["config"]
    messages = conversation_state["messages"]
    metadata = conversation_state["metadata"]
    branch_point = conversation_state["branch_point"]

    # Show what we found
    info_lines = [
        f"Source: {source_exp_dir.name}",
        f"Conversation: {conversation_id}",
        f"Branch point: Turn {branch_point} of {len(messages)}",
        f"Original models: {original_config['agent_a_model']} ↔ {original_config['agent_b_model']}",
    ]

    display.info("\n".join(info_lines), title="◆ Branch Source", use_panel=True)

    # Build new configuration
    branch_config = original_config.copy()

    # Apply overrides
    if agent_a:
        try:
            branch_config["agent_a_model"] = validate_model_id(agent_a)[0]
        except ValueError as e:
            display.error(f"Invalid agent A model: {e}")
            return

    if agent_b:
        try:
            branch_config["agent_b_model"] = validate_model_id(agent_b)[0]
        except ValueError as e:
            display.error(f"Invalid agent B model: {e}")
            return

    # Temperature overrides
    if temperature is not None:
        branch_config["temperature_a"] = temperature
        branch_config["temperature_b"] = temperature
    if temp_a is not None:
        branch_config["temperature_a"] = temp_a
    if temp_b is not None:
        branch_config["temperature_b"] = temp_b

    # Awareness overrides
    if awareness:
        branch_config["awareness_a"] = awareness
        branch_config["awareness_b"] = awareness
    if awareness_a:
        branch_config["awareness_a"] = awareness_a
    if awareness_b:
        branch_config["awareness_b"] = awareness_b

    # Other overrides
    if max_turns is not None:
        branch_config["max_turns"] = max_turns

    # Generate name if not provided
    if not name:
        name = f"{generate_experiment_name()}_branch"
        display.dim(f"Generated branch name: {name}")

    # Save as spec if requested
    if spec:
        spec_data = {
            "name": name,
            "agent_a_model": branch_config["agent_a_model"],
            "agent_b_model": branch_config["agent_b_model"],
            "repetitions": repetitions,
            "max_turns": branch_config["max_turns"],
            "temperature_a": branch_config.get("temperature_a"),
            "temperature_b": branch_config.get("temperature_b"),
            "awareness_a": branch_config.get("awareness_a", "basic"),
            "awareness_b": branch_config.get("awareness_b", "basic"),
            "branch_from": {
                "conversation_id": conversation_id,
                "turn": branch_point,
                "experiment_id": metadata.get("original_experiment_id"),
            },
            "initial_messages": [
                {"role": msg.role, "content": msg.content} for msg in messages
            ],
        }

        try:
            with open(spec, "w") as f:
                yaml.dump(spec_data, f, default_flow_style=False)
            display.info(f"Saved branch spec to: {spec}")
        except Exception as e:
            display.error(f"Failed to save spec: {e}")
            return

    # Show branch configuration
    changes = []
    if branch_config["agent_a_model"] != original_config["agent_a_model"]:
        changes.append(
            f"Agent A: {original_config['agent_a_model']} → {branch_config['agent_a_model']}"
        )
    if branch_config["agent_b_model"] != original_config["agent_b_model"]:
        changes.append(
            f"Agent B: {original_config['agent_b_model']} → {branch_config['agent_b_model']}"
        )
    if branch_config.get("temperature_a") != original_config.get("temperature_a"):
        changes.append(
            f"Temp A: {original_config.get('temperature_a', 'default')} → {branch_config.get('temperature_a')}"
        )
    if branch_config.get("temperature_b") != original_config.get("temperature_b"):
        changes.append(
            f"Temp B: {original_config.get('temperature_b', 'default')} → {branch_config.get('temperature_b')}"
        )

    if changes:
        display.info("\n".join(changes), title="◆ Branch Changes", use_panel=True)
    else:
        display.info("No parameter changes (exact replay)", use_panel=False)

    # Create experiment configuration
    config = ExperimentConfig(
        name=name,
        agent_a_model=branch_config["agent_a_model"],
        agent_b_model=branch_config["agent_b_model"],
        repetitions=repetitions,
        max_turns=branch_config["max_turns"],
        temperature_a=branch_config.get("temperature_a"),
        temperature_b=branch_config.get("temperature_b"),
        custom_prompt=branch_config.get("initial_prompt"),
        awareness_a=branch_config.get("awareness_a", "basic"),
        awareness_b=branch_config.get("awareness_b", "basic"),
        first_speaker=branch_config.get("first_speaker", "agent_a"),
        prompt_tag=branch_config.get("prompt_tag"),
        # Branch metadata
        branch_from_conversation=conversation_id,
        branch_from_turn=branch_point,
        branch_messages=messages,  # Pass the pre-populated messages
    )

    # Validate configuration
    errors = config.validate()
    if errors:
        error_msg = "Configuration errors:\n\n"
        for error in errors:
            error_msg += f"  • {error}\n"
        display.error(error_msg.rstrip(), use_panel=True)
        return

    # Validate API keys before starting daemon
    from ..providers.api_key_manager import APIKeyManager
    from ..config.models import get_model_config
    
    providers = set()
    agent_a_config = get_model_config(branch_config["agent_a_model"])
    agent_b_config = get_model_config(branch_config["agent_b_model"])
    if agent_a_config:
        providers.add(agent_a_config.provider)
    if agent_b_config:
        providers.add(agent_b_config.provider)
    
    try:
        # Check all providers have API keys before starting
        APIKeyManager.validate_required_providers(list(providers))
    except Exception as e:
        # Show friendly error message in the CLI
        display.error(str(e), title="Missing API Keys", use_panel=True)
        return

    # Start the branched experiment
    base_dir = get_experiments_dir()
    manager = ExperimentManager(base_dir=base_dir)

    try:
        # Start via manager
        exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)

        # Show start message
        console.print(f"\n[#a3be8c]✓ Started branch: {exp_id}[/#a3be8c]")

        if quiet:
            # Quiet mode: show commands and exit
            console.print(
                "\n[#4c566a]Running in background. Check progress:[/#4c566a]"
            )
            cmd_lines = [
                "pidgin monitor              # Monitor all experiments",
                f"pidgin stop {name}    # Stop by name",
                f"pidgin stop {exp_id[:8]}  # Stop by ID",
            ]
            display.info("\n".join(cmd_lines), title="Commands", use_panel=True)
        else:
            # Show live display
            console.print(
                "[#4c566a]Ctrl+C to exit display • experiment continues[/#4c566a]"
            )
            console.print()

            from ..experiments.display_runner import run_display

            try:
                asyncio.run(run_display(exp_id, "chat"))

                # Show completion info
                exp_dir = get_experiments_dir() / exp_id
                manifest_path = exp_dir / "manifest.json"

                if manifest_path.exists():
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)

                    completed = manifest.get("completed_conversations", 0)
                    # _failed = manifest.get("failed_conversations", 0)  # For future use
                    total = manifest.get("total_conversations", repetitions)

                    display.info(
                        f"Branch complete: {completed}/{total} conversations",
                        context=f"Output: {exp_dir}",
                        use_panel=True,
                    )

            except KeyboardInterrupt:
                console.print()
                display.info(
                    "Display exited. Branch continues in background.", use_panel=False
                )

    except Exception as e:
        display.error(f"Failed to start branch: {str(e)}", use_panel=True)
        raise


def branch_from_spec(spec_file: str):
    """Run a branch from a YAML specification.

    This allows replaying branches with saved configurations.
    """
    try:
        with open(spec_file, "r") as f:
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

    except Exception as e:
        display.error(f"Failed to load branch spec: {e}")
