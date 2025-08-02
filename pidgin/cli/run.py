# pidgin/cli/run.py
"""Unified run command for conversations and experiments."""

import asyncio
from typing import Optional

import rich_click as click
from rich.console import Console

from ..config.models import get_model_config
from ..experiments import ExperimentConfig
from ..ui.display_utils import DisplayUtils
from .config_builder import ConfigBuilder
from .constants import (
    DEFAULT_TURNS,
    NORD_BLUE,
    NORD_DARK,
    NORD_RED,
)
from .daemon_launcher import DaemonLauncher
from .display_manager import DisplayManager
from .helpers import (
    format_model_display,
    validate_model_id,
)
from .model_selector import ModelSelector
from .spec_loader import SpecLoader

console = Console()
display = DisplayUtils(console)

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD


@click.command()
@click.argument(
    "spec_file", required=False, type=click.Path(exists=True), metavar="[SPEC_FILE]"
)
@click.option(
    "--agent-a", "-a", help="* First agent model (e.g., gpt-4, claude, gemini-1.5-pro)"
)
@click.option("--agent-b", "-b", help="* Second agent model")
@click.option("--prompt", "-p", help="Initial prompt to start the conversation")
@click.option(
    "--turns",
    "-t",
    type=click.IntRange(1, 1000),
    default=DEFAULT_TURNS,
    help=f"Maximum number of conversation turns (default: {DEFAULT_TURNS})",
)
@click.option(
    "--repetitions",
    "-r",
    type=click.IntRange(1, 10000),
    default=1,
    help="Number of conversations to run (default: 1)",
)
@click.option(
    "--temperature",
    type=click.FloatRange(0.0, 2.0),
    help="Temperature for both agents (0.0-2.0)",
)
@click.option(
    "--temp-a", type=click.FloatRange(0.0, 2.0), help="Temperature for agent A only"
)
@click.option(
    "--temp-b", type=click.FloatRange(0.0, 2.0), help="Temperature for agent B only"
)
@click.option("--output", "-o", help="Custom output directory")
@click.option(
    "--dimension", "-d", multiple=True, help="Predefined conversation dimensions"
)
@click.option(
    "--convergence-threshold",
    type=float,
    help="Stop when convergence score exceeds this (0.0-1.0)",
)
@click.option(
    "--convergence-action",
    type=click.Choice(["notify", "pause", "stop"]),
    help="Action when convergence threshold is reached",
)
@click.option(
    "--convergence-profile",
    type=click.Choice(["balanced", "structural", "semantic", "strict"]),
    default="balanced",
    help="Convergence weight profile (default: balanced)",
)
@click.option(
    "--first-speaker",
    type=click.Choice(["a", "b", "random"]),
    default="a",
    help="Which agent speaks first",
)
@click.option("--choose-names", is_flag=True, help="Let agents choose their own names")
@click.option(
    "-w",
    "--awareness",
    default="basic",
    help="Awareness level (none/basic/firm/research) or custom YAML file",
)
@click.option(
    "--awareness-a", help="Override awareness for agent A (level or YAML file)"
)
@click.option(
    "--awareness-b", help="Override awareness for agent B (level or YAML file)"
)
@click.option(
    "--show-system-prompts", is_flag=True, help="Display system prompts at start"
)
@click.option(
    "--meditation", is_flag=True, help="Meditation mode: one agent faces silence"
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Run in background with notification when complete",
)
@click.option(
    "--tail", is_flag=True, help="Show formatted event stream during conversation"
)
@click.option("--notify", is_flag=True, help="Send notification when complete")
@click.option(
    "--name", "-n", help="Name for the experiment (auto-generated if not provided)"
)
@click.option(
    "--max-parallel",
    type=click.IntRange(1, 50),
    default=1,
    help="Max parallel conversations (default: 1, sequential)",
)
@click.option(
    "--prompt-tag",
    default="[HUMAN]",
    help='Tag to prefix the initial prompt (default: "[HUMAN]", use "" to disable)',
)
@click.option(
    "--allow-truncation",
    is_flag=True,
    help="Allow messages to be truncated to fit context windows (default: disabled)",
)
def run(
    spec_file,
    agent_a,
    agent_b,
    prompt,
    turns,
    repetitions,
    temperature,
    temp_a,
    temp_b,
    output,
    dimension,
    convergence_threshold,
    convergence_action,
    convergence_profile,
    first_speaker,
    choose_names,
    awareness,
    awareness_a,
    awareness_b,
    show_system_prompts,
    meditation,
    quiet,
    tail,
    notify,
    name,
    max_parallel,
    prompt_tag,
    allow_truncation,
):
    """Run AI conversations - single or multiple.

    This unified command runs conversations between two AI agents.
    By default shows the conversation messages as they are generated.

    [bold]EXAMPLES:[/bold]

    [#4c566a]From YAML spec:     [/#4c566a]
      pidgin run experiment.yaml

    [#4c566a]Basic conversation: [/#4c566a]
      pidgin run -a claude -b gpt

    [#4c566a]Event stream:       [/#4c566a]
      pidgin run -a claude -b gpt --tail

    [#4c566a]Run in background:  [/#4c566a]
      pidgin run -a claude -b gpt --quiet

    [#4c566a]Multiple runs:      [/#4c566a]
      pidgin run -a claude -b gpt -r 20 -n "test"

    [#4c566a]Dimensional prompt: [/#4c566a]
      pidgin run -a claude -b gpt -d philosophy

    [#4c566a]Meditation mode:    [/#4c566a]
      pidgin run -a claude --meditation
    """
    # Check if a YAML spec file was provided
    if spec_file and spec_file.endswith((".yaml", ".yml")):
        spec_loader = SpecLoader()
        try:
            # Load and validate spec
            spec = spec_loader.load_spec(spec_file)
            spec_loader.validate_spec(spec)
            
            # Convert to config
            config = spec_loader.spec_to_config(spec)
            
            # Show spec info
            spec_loader.show_spec_info(spec_file, config)
            
            # Get model display names for _run_conversations
            agent_a_config = get_model_config(config.agent_a_model)
            agent_b_config = get_model_config(config.agent_b_model)
            agent_a_name = agent_a_config.display_name if agent_a_config else config.agent_a_model
            agent_b_name = agent_b_config.display_name if agent_b_config else config.agent_b_model
            
            # Run the experiment
            _run_conversations(
                config.agent_a_model,
                config.agent_b_model,
                agent_a_name,
                agent_b_name,
                config.repetitions,
                config.max_turns,
                config.temperature_a,
                config.temperature_b,
                config.custom_prompt or "Hello",
                config.dimensions,
                config.name,
                config.max_parallel,
                config.convergence_threshold,
                config.convergence_action,
                config.awareness,
                config.awareness_a,
                config.awareness_b,
                config.choose_names,
                config.display_mode == "quiet",
                config.display_mode == "quiet" or spec.get("notify", False),
                config.display_mode,
                config.first_speaker,
                spec.get("output"),  # output_dir not in ExperimentConfig
                config.prompt_tag,
                config.allow_truncation,
            )
            return
        except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
            # Errors are already displayed by spec_loader
            return
        except Exception as e:
            display.error(f"Unexpected error: {e}")
            return

    # Handle display mode flags
    display_manager = DisplayManager(console)
    if not display_manager.validate_display_flags(quiet, tail):
        return
    
    display_mode, quiet, notify = display_manager.determine_display_mode(quiet, tail, max_parallel)

    # Handle meditation mode
    agent_a, agent_b = display_manager.handle_meditation_mode(meditation, agent_a, agent_b)

    # Interactive model selection if not provided
    model_selector = ModelSelector()
    
    if not agent_a:
        try:
            agent_a = model_selector.select_model("Select first agent (Agent A)")
            if not agent_a:
                return
        except (KeyboardInterrupt, EOFError) as e:
            display_manager.handle_model_selection_error(e, type(e).__name__)
            return
        except Exception as e:
            display_manager.handle_model_selection_error(e, "Exception")
            return

    if not agent_b:
        try:
            agent_b = model_selector.select_model("Select second agent (Agent B)")
            if not agent_b:
                return
        except (KeyboardInterrupt, EOFError) as e:
            display_manager.handle_model_selection_error(e, type(e).__name__)
            return
        except Exception as e:
            display_manager.handle_model_selection_error(e, "Exception")
            return

    # Validate models
    try:
        model_selector.validate_models(agent_a, agent_b)
    except ValueError as e:
        display.error(str(e), use_panel=False)
        return

    # Determine experiment display mode
    experiment_display_mode = display_manager.determine_experiment_display_mode(
        display_mode, max_parallel, quiet
    )
    
    # Build configuration using ConfigBuilder
    config_builder = ConfigBuilder()
    try:
        config, agent_a_name, agent_b_name = config_builder.build_config(
            agent_a=agent_a,
            agent_b=agent_b,
            repetitions=repetitions,
            max_turns=turns,
            temperature=temperature,
            temp_a=temp_a,
            temp_b=temp_b,
            prompt=prompt,
            dimensions=list(dimension) if dimension else None,
            name=name,
            max_parallel=max_parallel,
            convergence_threshold=convergence_threshold,
            convergence_action=convergence_action,
            convergence_profile=convergence_profile,
            awareness=awareness,
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            first_speaker=first_speaker,
            display_mode=experiment_display_mode,
            prompt_tag=prompt_tag,
            allow_truncation=allow_truncation,
        )
    except ValueError as e:
        display.error(str(e), use_panel=False)
        return
    
    # Extract values for _run_conversations
    initial_prompt = config.custom_prompt or "Hello"

    # Always use the unified execution path
    _run_conversations(
        config.agent_a_model,
        config.agent_b_model,
        agent_a_name,
        agent_b_name,
        config.repetitions,
        config.max_turns,
        config.temperature_a,
        config.temperature_b,
        initial_prompt,
        config.dimensions,
        config.name,
        config.max_parallel,
        config.convergence_threshold,
        config.convergence_action,
        config.awareness,
        config.awareness_a,
        config.awareness_b,
        config.choose_names,
        quiet,
        notify,
        display_mode,
        config.first_speaker,
        output,
        config.prompt_tag,
        config.allow_truncation,
    )



def _run_conversations(
    agent_a_id,
    agent_b_id,
    agent_a_name,
    agent_b_name,
    repetitions,
    max_turns,
    temp_a,
    temp_b,
    initial_prompt,
    dimensions,
    name,
    max_parallel,
    convergence_threshold,
    convergence_action,
    awareness,
    awareness_a,
    awareness_b,
    choose_names,
    quiet,
    notify,
    display_mode,
    first_speaker_id,
    output_dir,
    prompt_tag,
    allow_truncation,
):
    """Run conversations using the unified execution path."""
    # Create experiment configuration
    config = ExperimentConfig(
        name=name,
        agent_a_model=agent_a_id,
        agent_b_model=agent_b_id,
        repetitions=repetitions,
        max_turns=max_turns,
        temperature_a=temp_a,
        temperature_b=temp_b,
        custom_prompt=initial_prompt if initial_prompt != "Hello" else None,
        dimensions=list(dimensions) if dimensions else None,
        max_parallel=max_parallel,
        convergence_threshold=convergence_threshold,
        convergence_action=convergence_action,
        awareness=awareness,
        awareness_a=awareness_a,
        awareness_b=awareness_b,
        choose_names=choose_names,
        first_speaker=first_speaker_id,
        display_mode=display_mode,
        prompt_tag=prompt_tag,
        allow_truncation=allow_truncation,
    )

    # Show configuration using ConfigBuilder
    config_builder = ConfigBuilder()
    config_builder.show_config_info(config, agent_a_name, agent_b_name, initial_prompt)

    # Launch daemon
    daemon_launcher = DaemonLauncher(console)
    try:
        exp_id = daemon_launcher.start_daemon(config)
    except Exception:
        # Error already displayed by daemon launcher
        return

    if quiet:
        # Quiet mode: just show commands and exit
        daemon_launcher.show_quiet_mode_info(exp_id, config.name)
    else:
        # Non-quiet mode: show live display
        daemon_launcher.show_interactive_mode_info()
        
        # Run display and handle completion
        asyncio.run(
            daemon_launcher.run_display_and_handle_completion(
                exp_id,
                config.name,
                display_mode,
                notify,
                config.repetitions,
            )
        )


