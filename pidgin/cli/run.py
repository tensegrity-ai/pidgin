# pidgin/cli/run.py
"""Unified run command for conversations and experiments."""

import asyncio
import json
from datetime import datetime
from typing import Optional

import rich_click as click
import yaml
from rich.console import Console

from ..config.defaults import get_smart_convergence_defaults
from ..config.models import MODELS, get_model_config
from ..config.resolution import resolve_temperatures
from ..experiments import ExperimentConfig, ExperimentManager
from ..io.paths import get_experiments_dir
from ..ui.display_utils import DisplayUtils
from .constants import (
    DEFAULT_TURNS,
    MODEL_GLYPHS,
    NORD_BLUE,
    NORD_DARK,
    NORD_RED,
)
from .helpers import (
    build_initial_prompt,
    check_ollama_available,
    format_model_display,
    parse_dimensions,
    validate_model_id,
)
from .name_generator import generate_experiment_name
from .notify import send_notification

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
        try:
            # Load YAML spec
            with open(spec_file, "r") as f:
                spec = yaml.safe_load(f)

            # Run from spec
            _run_from_spec(spec, spec_file)
            return
        except FileNotFoundError:
            display.error(f"Spec file not found: {spec_file}")
            return
        except yaml.YAMLError as e:
            display.error(f"Invalid YAML in {spec_file}: {e}")
            return
        except Exception as e:
            display.error(f"Error loading spec: {e}")
            return

    # Handle display mode flags
    mode_count = sum([quiet, tail])
    if mode_count > 1:
        console.print(
            f"[{NORD_RED}]Error: Can only use one of --quiet or --tail[/{NORD_RED}]"
        )
        return

    if quiet:
        display_mode = "quiet"
        # Quiet mode should run in background and notify
        notify = True
    elif tail:
        display_mode = "tail"  # Show formatted event stream
    else:
        display_mode = "chat"  # Default: show conversation messages

    # Handle meditation mode
    if meditation:
        if not agent_a:
            agent_a = "claude"
        if not agent_b:
            agent_b = "silent"
        console.print(
            f"\n[{NORD_BLUE}]◆ Meditation mode: {agent_a} → silence[/{NORD_BLUE}]"
        )

    # Interactive model selection if not provided
    if not agent_a:
        try:
            agent_a = _prompt_for_model("Select first agent (Agent A)")
            if not agent_a:
                return
        except (KeyboardInterrupt, EOFError):
            console.print()  # Add newline
            display.warning(
                "Model selection cancelled",
                context=(
                    "Use -a and -b flags to specify models.\n"
                    "Example: pidgin run -a claude -b gpt"
                ),
                use_panel=False,
            )
            return
        except Exception as e:
            console.print()  # Add newline
            display.error(
                f"Error during model selection: {e}",
                context=(
                    "Use -a and -b flags to specify models directly.\n"
                    "Example: pidgin run -a claude -b gpt"
                ),
                use_panel=False,
            )
            return

    if not agent_b:
        try:
            agent_b = _prompt_for_model("Select second agent (Agent B)")
            if not agent_b:
                return
        except (KeyboardInterrupt, EOFError):
            console.print()  # Add newline
            display.warning(
                "Model selection cancelled",
                context=(
                    "Use -a and -b flags to specify models.\n"
                    "Example: pidgin run -a claude -b gpt"
                ),
                use_panel=False,
            )
            return
        except Exception as e:
            console.print()  # Add newline
            display.error(
                f"Error during model selection: {e}",
                context=(
                    "Use -a and -b flags to specify models directly.\n"
                    "Example: pidgin run -a claude -b gpt"
                ),
                use_panel=False,
            )
            return

    # Validate models
    try:
        agent_a_id, agent_a_name = validate_model_id(agent_a)
        agent_b_id, agent_b_name = validate_model_id(agent_b)
    except ValueError as e:
        display.error(str(e), use_panel=False)
        return

    # Handle temperature settings
    temp_a, temp_b = resolve_temperatures(temperature, temp_a, temp_b)

    # Parse and validate dimensions
    if dimension:
        dimension = parse_dimensions(list(dimension))

    # Build initial prompt
    initial_prompt = build_initial_prompt(prompt, list(dimension))

    # Set convergence profile in config
    from ..config import get_config

    config = get_config()
    config.set("convergence.profile", convergence_profile)

    # Add smart convergence defaults for API models
    if convergence_threshold is None:
        default_threshold, default_action = get_smart_convergence_defaults(
            agent_a_id, agent_b_id
        )
        if default_threshold is not None:
            convergence_threshold = default_threshold
            if convergence_action is None:
                convergence_action = default_action
            # Log this default
            display.dim(
                f"Using default convergence threshold: {convergence_threshold} "
                f"→ {convergence_action}"
            )

    # Default convergence action
    if convergence_action is None:
        convergence_action = "stop"  # Always use 'stop' as default

    # Force quiet mode if parallel execution
    if max_parallel > 1 and not quiet:
        quiet = True
        display.warning(
            f"Parallel execution (max_parallel={max_parallel}) requires quiet mode",
            use_panel=False,
        )

    # Generate fun name if not provided
    if not name:
        name = generate_experiment_name()
        display.dim(f"Generated experiment name: {name}")

    # Determine first speaker
    if first_speaker == "random":
        import random

        first_speaker = random.choice(["a", "b"])
    first_speaker_id = f"agent_{first_speaker}"

    # Always use the unified execution path
    _run_conversations(
        agent_a_id,
        agent_b_id,
        agent_a_name,
        agent_b_name,
        repetitions,
        turns,
        temp_a,
        temp_b,
        initial_prompt,
        dimension,
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
        output,
        prompt_tag,
    )


def _run_from_spec(spec, spec_file):
    """Run experiment from YAML specification.

    Args:
        spec: Loaded YAML specification dictionary
        spec_file: Path to the spec file (for error messages)
    """
    # Map YAML fields to ExperimentConfig fields
    # Handle both direct field names and nested structures

    # Required fields
    if "agent_a_model" not in spec or "agent_b_model" not in spec:
        # Also check for shorthand
        if "agent_a" in spec and "agent_b" in spec:
            spec["agent_a_model"] = spec.pop("agent_a")
            spec["agent_b_model"] = spec.pop("agent_b")
        else:
            display.error(
                f"Missing required fields in {spec_file}",
                context=(
                    "Must specify agent_a_model and agent_b_model "
                    "(or agent_a and agent_b)"
                ),
            )
            return

    # Handle model validation
    try:
        agent_a_id = validate_model_id(spec["agent_a_model"])
        agent_b_id = validate_model_id(spec["agent_b_model"])
    except ValueError as e:
        display.error(f"Invalid model in {spec_file}: {e}")
        return

    # Get model configs for display names
    agent_a_config = get_model_config(agent_a_id)
    agent_b_config = get_model_config(agent_b_id)
    agent_a_name = agent_a_config.get("display_name", agent_a_id)
    agent_b_name = agent_b_config.get("display_name", agent_b_id)

    # Map other fields with defaults
    name = spec.get("name", generate_experiment_name())
    repetitions = spec.get("repetitions", 1)
    max_turns = spec.get("max_turns", spec.get("turns", DEFAULT_TURNS))

    # Temperature handling
    temp_a = spec.get("temperature_a", spec.get("temperature"))
    temp_b = spec.get("temperature_b", spec.get("temperature"))

    # Prompt handling
    initial_prompt = spec.get("custom_prompt", spec.get("prompt", "Hello"))
    dimensions = spec.get("dimensions", spec.get("dimension"))

    # Convergence settings
    convergence_threshold = spec.get("convergence_threshold")
    convergence_action = spec.get(
        "convergence_action", "stop" if convergence_threshold else None
    )

    # Awareness settings
    awareness = spec.get("awareness", "basic")
    awareness_a = spec.get("awareness_a")
    awareness_b = spec.get("awareness_b")

    # Other settings
    choose_names = spec.get("choose_names", False)
    max_parallel = spec.get("max_parallel", 1)
    first_speaker = spec.get("first_speaker", "agent_a")
    display_mode = spec.get("display_mode", "chat")
    prompt_tag = spec.get("prompt_tag", "[HUMAN]")

    # Notification settings
    quiet = display_mode == "quiet"
    notify = spec.get("notify", quiet)

    # Output directory
    output_dir = spec.get("output")

    # Show spec info
    display.info(
        f"Loading experiment from: {spec_file}",
        context=(
            f"Name: {name}\n"
            f"Agents: {agent_a_name} ↔ {agent_b_name}\n"
            f"Repetitions: {repetitions}"
        ),
    )

    # Run the experiment
    _run_conversations(
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
        first_speaker,
        output_dir,
        prompt_tag,
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
):
    """Run conversations using the unified execution path."""
    # Determine display mode for experiments
    # For parallel execution or quiet mode, don't use interactive displays
    if max_parallel > 1 or quiet:
        experiment_display_mode = "none"
        if display_mode in ["tail", "chat"] and max_parallel > 1:
            display.warning(
                f"--{display_mode} is not supported with parallel execution",
                use_panel=False,
            )
    else:
        # Non-quiet mode can use any display mode
        experiment_display_mode = display_mode

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
        display_mode=experiment_display_mode,
        prompt_tag=prompt_tag,
    )

    # Show configuration
    config_lines = []
    config_lines.append(f"Name: {name}")
    config_lines.append(
        f"Models: {format_model_display(agent_a_id)} ↔ "
        f"{format_model_display(agent_b_id)}"
    )
    config_lines.append(f"Conversations: {repetitions}")
    config_lines.append(f"Turns per conversation: {max_turns}")

    if max_parallel > 1:
        config_lines.append(f"Parallel execution: {max_parallel}")

    if initial_prompt != "Hello":
        if len(initial_prompt) > 50:
            config_lines.append(f"Initial prompt: {initial_prompt[:50]}...")
        else:
            config_lines.append(f"Initial prompt: {initial_prompt}")

    if temp_a is not None or temp_b is not None:
        temp_parts = []
        if temp_a is not None:
            temp_parts.append(f"A: {temp_a}")
        if temp_b is not None:
            temp_parts.append(f"B: {temp_b}")
        config_lines.append(f"Temperature: {', '.join(temp_parts)}")

    if convergence_threshold:
        config_lines.append(
            f"Convergence: {convergence_threshold} → {convergence_action}"
        )

    display.info(
        "\n".join(config_lines), title="◆ Experiment Configuration", use_panel=True
    )

    # Check if experiment already exists
    from ..io.jsonl_reader import JSONLExperimentReader

    jsonl_reader = JSONLExperimentReader(get_experiments_dir())
    experiments = jsonl_reader.list_experiments()
    existing = next((exp for exp in experiments if exp.get("name") == name), None)

    if existing:
        display.error(
            f"Experiment session '{name}' already exists",
            context=f"Use 'pidgin attach {name}' to monitor",
            use_panel=False,
        )
        return

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
    agent_a_config = get_model_config(agent_a_id)
    agent_b_config = get_model_config(agent_b_id)
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

    # Always run via daemon
    base_dir = get_experiments_dir()
    manager = ExperimentManager(base_dir=base_dir)

    try:
        # Always start via manager (creates daemon + PID file)
        exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)

        # Show start message
        console.print(f"\n[#a3be8c]✓ Started: {exp_id}[/#a3be8c]")

        if quiet:
            # Quiet mode: just show commands and exit
            console.print(
                "\n[#4c566a]Running in background. Check progress:[/#4c566a]"
            )
            cmd_lines = []
            cmd_lines.append("pidgin monitor              # Monitor all experiments")
            cmd_lines.append(f"pidgin stop {name}    # Stop by name")
            cmd_lines.append(f"pidgin stop {exp_id[:8]}  # Stop by ID")
            cmd_lines.append(f"tail -f {get_experiments_dir()}/{exp_id}/*.jsonl")
            display.info("\n".join(cmd_lines), title="Commands", use_panel=True)
        else:
            # Non-quiet mode: show live display
            console.print(
                f"[{NORD_DARK}]Ctrl+C to exit display • "
                f"experiment continues[/{NORD_DARK}]"
            )
            console.print()

            # Import the display runners
            from ..experiments.display_runner import run_display

            try:
                # Get the actual directory name
                exp_dir_name = manager.get_experiment_directory(exp_id)
                if not exp_dir_name:
                    display.error(f"Could not find directory for experiment {exp_id}")
                    return
                
                # Run the display (this will tail JSONL files and show live updates)
                asyncio.run(run_display(exp_dir_name, display_mode))

                # After display exits, show completion info
                exp_dir = get_experiments_dir() / exp_dir_name
                manifest_path = exp_dir / "manifest.json"

                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)

                        # Extract statistics from manifest
                        completed = manifest.get("completed_conversations", 0)
                        failed = manifest.get("failed_conversations", 0)
                        total = manifest.get("total_conversations", repetitions)
                        status = manifest.get("status", "completed")

                        # Calculate duration
                        start_time = manifest.get("started_at")
                        end_time = manifest.get("completed_at")
                        if start_time and end_time:
                            start_dt = datetime.fromisoformat(
                                start_time.replace("Z", "+00:00")
                            )
                            end_dt = datetime.fromisoformat(
                                end_time.replace("Z", "+00:00")
                            )
                            duration = (end_dt - start_dt).total_seconds()
                        else:
                            duration = 0

                        # Display completion info
                        display.experiment_complete(
                            name=name,
                            experiment_id=exp_id,
                            completed=completed,
                            failed=failed,
                            total=total,
                            duration_seconds=duration,
                            status=status,
                            experiment_dir=str(exp_dir),
                        )

                        if notify and status == "completed":
                            send_notification(
                                title="Pidgin Experiment Complete",
                                message=(
                                    f"Experiment '{name}' has finished "
                                    f"({completed}/{total} conversations)"
                                ),
                            )
                        else:
                            # Terminal bell notification
                            print("\a", end="", flush=True)
                    except Exception:
                        # If can't read manifest, just note that display exited
                        display.info(
                            (
                                "Display exited. Experiment continues "
                                "running in background."
                            ),
                            use_panel=False,
                        )
                else:
                    display.info(
                        "Display exited. Experiment continues running in background.",
                        use_panel=False,
                    )

            except KeyboardInterrupt:
                # Ctrl+C just exits display, not the experiment
                console.print()
                display.info(
                    "Display exited. Experiment continues running in background.",
                    use_panel=False,
                )
                console.print("\n[#4c566a]Check progress with:[/#4c566a]")
                console.print("  pidgin monitor")
                console.print(f"  pidgin stop {name}")

    except Exception as e:
        display.error(f"Failed to start experiment: {str(e)}", use_panel=True)
        raise


def _prompt_for_model(prompt_text: str) -> Optional[str]:
    """Interactive model selection."""
    display.info(prompt_text, use_panel=False)

    # Group models by provider
    providers = {}
    for model_id, config in MODELS.items():
        if model_id == "silent":  # Skip silent model in normal selection
            continue
        if config.provider not in providers:
            providers[config.provider] = []
        providers[config.provider].append((model_id, config))

    # Show available models
    idx = 1
    model_map = {}

    for provider in ["openai", "anthropic", "google", "xai", "local"]:
        if provider not in providers:
            continue

        # Show provider section
        display.dim(f"\n{provider.title()}:")

        for model_id, config in providers[provider]:
            glyph = MODEL_GLYPHS.get(model_id, "●")
            display.dim(f"  {idx}. {glyph} {config.shortname}")
            model_map[str(idx)] = model_id
            idx += 1

    # Add option for custom local model
    display.dim("\nOther:")
    display.dim(f"  {idx}. ▸ Custom local model (requires Ollama)")

    # Get selection
    try:
        selection = console.input(
            f"\n[{NORD_BLUE}]Enter selection (1-{idx}) or model name: [/{NORD_BLUE}]"
        )
    except (KeyboardInterrupt, EOFError):
        # User cancelled
        return None

    if selection in model_map:
        return model_map[selection]
    elif selection == str(idx):
        # Custom local model
        if not check_ollama_available():
            display.error(
                "Ollama is not running. Start it with 'ollama serve'", use_panel=False
            )
            return None
        try:
            model_name = console.input(
                f"[{NORD_BLUE}]Enter local model name: [/{NORD_BLUE}]"
            )
        except (KeyboardInterrupt, EOFError):
            return None
        return f"local:{model_name}"
    else:
        # Try as direct model ID
        try:
            validate_model_id(selection)
            return selection
        except ValueError:
            display.error("Invalid selection", use_panel=False)
            return None
