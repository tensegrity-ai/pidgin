"""Unified run command for conversations and experiments."""

from typing import Optional

import rich_click as click
from rich.console import Console

from .constants import DEFAULT_TURNS
from .run_handlers import CommandHandler, RunConfig

console = Console()


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
@click.option("--think", is_flag=True, help="Enable extended thinking for both agents")
@click.option(
    "--think-a", is_flag=True, help="Enable extended thinking for agent A only"
)
@click.option(
    "--think-b", is_flag=True, help="Enable extended thinking for agent B only"
)
@click.option(
    "--think-budget",
    type=click.IntRange(1000, 100000),
    default=None,
    help="Max thinking tokens (default: 10000)",
)
@click.option("--output", "-o", help="Custom output directory")
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
    spec_file: Optional[str],
    agent_a: Optional[str],
    agent_b: Optional[str],
    prompt: Optional[str],
    turns: int,
    repetitions: int,
    temperature: Optional[float],
    temp_a: Optional[float],
    temp_b: Optional[float],
    think: bool,
    think_a: bool,
    think_b: bool,
    think_budget: Optional[int],
    output: Optional[str],
    convergence_threshold: Optional[float],
    convergence_action: Optional[str],
    convergence_profile: str,
    choose_names: bool,
    awareness: str,
    awareness_a: Optional[str],
    awareness_b: Optional[str],
    show_system_prompts: bool,
    meditation: bool,
    quiet: bool,
    tail: bool,
    notify: bool,
    name: Optional[str],
    max_parallel: int,
    prompt_tag: str,
    allow_truncation: bool,
) -> None:
    """Run AI conversations between two agents.

    [bold]EXAMPLES:[/bold]

      pidgin run experiment.yaml        # From YAML spec
      pidgin run -a claude -b gpt        # Basic conversation
      pidgin run -a claude -b gpt --tail # Event stream
      pidgin run -a claude -b gpt -q     # Run in background
      pidgin run -a claude -b gpt -r 20  # Multiple runs
      pidgin run -a claude -b gpt -p "Explore philosophy together"
      pidgin run -a claude --meditation  # Meditation mode
    """
    # Build configuration from CLI arguments
    config = RunConfig.from_cli_args(
        spec_file=spec_file,
        agent_a=agent_a,
        agent_b=agent_b,
        prompt=prompt,
        turns=turns,
        repetitions=repetitions,
        temperature=temperature,
        temp_a=temp_a,
        temp_b=temp_b,
        think=think,
        think_a=think_a,
        think_b=think_b,
        think_budget=think_budget,
        output=output,
        convergence_threshold=convergence_threshold,
        convergence_action=convergence_action,
        convergence_profile=convergence_profile,
        choose_names=choose_names,
        awareness=awareness,
        awareness_a=awareness_a,
        awareness_b=awareness_b,
        show_system_prompts=show_system_prompts,
        meditation=meditation,
        quiet=quiet,
        tail=tail,
        notify=notify,
        name=name,
        max_parallel=max_parallel,
        prompt_tag=prompt_tag,
        allow_truncation=allow_truncation,
    )

    handler = CommandHandler(console)
    handler.handle_command(config)
