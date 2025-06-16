import os
# Force color output for rich-click
os.environ['FORCE_COLOR'] = '1'
os.environ['CLICOLOR_FORCE'] = '1'

# Configure rich-click BEFORE importing
import rich_click.rich_click as rc

# Force terminal and color detection
rc.COLOR_SYSTEM = "truecolor"
rc.FORCE_TERMINAL = True

# Configure rich console directly
from rich.console import Console
rc.CONSOLE = Console(force_terminal=True, color_system="truecolor")

rc.USE_RICH_MARKUP = True
rc.SHOW_ARGUMENTS = True
rc.GROUP_ARGUMENTS_OPTIONS = True
rc.SHOW_METAVARS_COLUMN = False
rc.APPEND_METAVARS_HELP = True
rc.MAX_WIDTH = 100

# Nord color scheme
rc.STYLE_OPTION = "bold #8fbcbb"  # Nord7 teal
rc.STYLE_ARGUMENT = "bold #88c0d0"  # Nord8 light blue
rc.STYLE_COMMAND = "bold #5e81ac"  # Nord10 blue
rc.STYLE_SWITCH = "#a3be8c"  # Nord14 green
rc.STYLE_METAVAR = "#d8dee9"  # Nord4 light gray
rc.STYLE_USAGE = "bold #8fbcbb"
rc.STYLE_OPTION_DEFAULT = "#4c566a"  # Nord3 dim gray
rc.STYLE_REQUIRED_SHORT = "bold #bf616a"  # Nord11 red
rc.STYLE_REQUIRED_LONG = "bold #bf616a"
rc.STYLE_HELPTEXT_FIRST_LINE = "bold"
rc.STYLE_HELPTEXT = "#d8dee9"  # Nord4 light gray
rc.STYLE_OPTION_HELP = "#d8dee9"  # Nord4 light gray for option descriptions

# Now import as click
import rich_click as click

import asyncio
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from .models import MODELS, get_model_config, get_models_by_provider
from .types import Agent
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.google import GoogleProvider
from .providers.xai import xAIProvider
from .config import Config, load_config
from .dimensional_prompts import DimensionalPromptGenerator

console = Console()


def _build_initial_prompt(
    custom_prompt: Optional[str],
    dimensions: Optional[str],
    puzzle: Optional[str] = None,
    experiment: Optional[str] = None,
    topic_content: Optional[str] = None,
) -> str:
    """Build initial prompt from custom prompt and/or dimensions."""
    parts = []

    # Add dimensional prompt if specified
    if dimensions:
        try:
            generator = DimensionalPromptGenerator()
            dimensional_prompt = generator.generate(
                dimensions,
                puzzle=puzzle,
                experiment=experiment,
                topic_content=topic_content,
            )
            parts.append(dimensional_prompt)
        except ValueError as e:
            console.print(f"[red]Error in dimensional prompt: {e}[/red]")
            raise click.Abort()

    # Add custom prompt if specified
    if custom_prompt:
        parts.append(custom_prompt)

    # If nothing specified, use default
    if not parts:
        return "Hello! I'm looking forward to our conversation."

    # Combine parts with space
    return " ".join(parts)


def get_provider_for_model(model: str):
    """Determine which provider to use based on the model name"""
    # Try to get model config first
    config = get_model_config(model)
    if config:
        if config.provider == "anthropic":
            return AnthropicProvider(config.model_id)
        elif config.provider == "openai":
            return OpenAIProvider(config.model_id)
        elif config.provider == "google":
            return GoogleProvider(config.model_id)
        elif config.provider == "xai":
            return xAIProvider(config.model_id)

    # Fallback to prefix matching for custom models
    if model.startswith("claude"):
        return AnthropicProvider(model)
    elif model.startswith("gpt") or model.startswith("o3") or model.startswith("o4"):
        return OpenAIProvider(model)
    elif model.startswith("gemini"):
        return GoogleProvider(model)
    elif model.startswith("grok"):
        return xAIProvider(model)
    else:
        raise ValueError(
            f"Unknown model type: {model}. Model should start with 'claude', 'gpt'/'o3'/'o4', 'gemini', or 'grok'"
        )


class BannerGroup(click.Group):
    """Custom group that shows banner before help"""

    def format_help(self, ctx, formatter):
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align

        console = Console()
        
        # Create the minimalist banner with Nord colors
        banner_text = Text()
        banner_text.append("pidgin v0.1.0", style="#d8dee9")  # nord4
        banner_text.append(" — ", style="#4c566a")  # nord3
        banner_text.append("linguistic emergence observatory", style="#8fbcbb")  # nord7
        
        # Create the separator line
        separator = "═" * 48
        
        # Combine into a panel with Nord styling
        content = Text()
        content.append(banner_text)
        content.append("\n")
        content.append(separator, style="#5e81ac")  # nord10
        
        # Create panel with Nord background color hint
        panel = Panel(
            Align.center(content),
            border_style="#5e81ac",  # nord10
            padding=(1, 2),
            style="on #2e3440",  # nord0 background hint
            expand=False  # Don't expand to full width
        )
        
        # Print left-aligned
        console.print()
        console.print(panel)
        console.print()
        
        super().format_help(ctx, formatter)


def create_config_templates():
    """Create all configuration templates and show usage instructions"""
    from datetime import datetime

    config_dir = Path.home() / ".pidgin"
    config_dir.mkdir(exist_ok=True)
    created_files = []

    # Puzzles template
    puzzle_path = config_dir / "puzzles.yaml"
    if not puzzle_path.exists():
        puzzle_content = f"""# Pidgin Custom Puzzle Library
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# Add your own puzzles here. They'll be available with:
#   pidgin chat -d collaboration:puzzles --puzzle your_puzzle_name
#
# Format:
#   puzzle_id:
#     content: "The puzzle question"
#     category: "type of puzzle" (optional)
#     difficulty: "easy/medium/hard" (optional)
#     answer: "The solution" (optional, for research tracking)
#     source: "Where it's from" (optional)

puzzles:
  # Example custom puzzles
  keyboard:
    content: "What has many keys but can't open any doors?"
    category: "objects"
    difficulty: "easy"
    answer: "A keyboard (piano or computer)"
    
  # Add your puzzles below:
  
"""
        with open(puzzle_path, "w") as f:
            f.write(puzzle_content)
        created_files.append(puzzle_path)

    # Thought experiments template
    exp_path = config_dir / "thought_experiments.yaml"
    if not exp_path.exists():
        exp_content = f"""# Pidgin Thought Experiment Library
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# Add your own thought experiments here. They'll be available with:
#   pidgin chat -d debate:thought_experiments --experiment your_experiment_name
#
# Format:
#   experiment_id:
#     content: "The thought experiment description"
#     category: "philosophical area" (optional)
#     source: "Original philosopher/paper" (optional)
#     year: "When it was proposed" (optional)
#     variants: ["list of variations"] (optional)

thought_experiments:
  # Example custom experiments
  ai_consciousness:
    content: "If an AI can perfectly simulate human responses to any question about its inner experience, including expressing uncertainty about consciousness, does it have inner experience?"
    category: "consciousness"
    source: "Contemporary AI ethics"
    
  # Add your experiments below:
  
"""
        with open(exp_path, "w") as f:
            f.write(exp_content)
        created_files.append(exp_path)

    # Dimensions template
    dim_path = config_dir / "dimensions.yaml"
    if not dim_path.exists():
        dim_content = f"""# Pidgin Custom Dimensions
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# Define custom dimensions for prompt generation.
# (This feature is planned for future releases)
#
# Format:
#   dimension_name:
#     description: "What this dimension represents"
#     required: false
#     values:
#       value_name: "Template or description"

custom_dimensions:
  # Example: Add a "persona" dimension
  # persona:
  #   description: "The conversational persona"
  #   required: false
  #   values:
  #     scientist: "As a curious scientist"
  #     artist: "From an artistic perspective" 
  #     child: "With childlike wonder"
  
"""
        with open(dim_path, "w") as f:
            f.write(dim_content)
        created_files.append(dim_path)

    # Display results
    console.print()
    if created_files:
        console.print("[bold green]✨ Configuration templates created![/bold green]\n")
        for file in created_files:
            console.print(f"  [green]✓[/green] {file}")
        console.print()
    else:
        console.print("[yellow]All configuration files already exist.[/yellow]\n")

    # Usage instructions
    console.print("[bold]How to use these files:[/bold]\n")

    console.print("[cyan]1. Custom Puzzles[/cyan] (~/.pidgin/puzzles.yaml)")
    console.print("   Add your own puzzles to use in conversations:")
    console.print(
        "   [dim]pidgin chat -d teaching:puzzles --puzzle your_puzzle_name[/dim]\n"
    )

    console.print(
        "[cyan]2. Thought Experiments[/cyan] (~/.pidgin/thought_experiments.yaml)"
    )
    console.print("   Add philosophical scenarios for debate:")
    console.print(
        "   [dim]pidgin chat -d debate:thought_experiments --experiment your_experiment[/dim]\n"
    )

    console.print("[cyan]3. Custom Dimensions[/cyan] (~/.pidgin/dimensions.yaml)")
    console.print(
        "   [dim]Note: Custom dimensions are planned for a future release.[/dim]\n"
    )

    console.print("[bold]Tips:[/bold]")
    console.print("  • Edit the YAML files with your favorite text editor")
    console.print("  • Follow the examples provided in each file")
    console.print("  • Your custom content will be immediately available\n")


@click.group(cls=BannerGroup, invoke_without_command=True)
@click.help_option("-h", "--help")
@click.option("--config", is_flag=True, help="Create configuration templates")
@click.pass_context
def cli(ctx, config):
    """AI conversation research tool for studying emergent communication patterns.
    
    Pidgin enables controlled experiments between AI agents to discover how they
    develop communication patterns, convergence behaviors, and linguistic adaptations.
    
    QUICK START:
        pidgin chat -a claude -b gpt -t 20
    
    EXAMPLES:
        # Basic conversation with custom prompt
        pidgin chat -a opus -b gpt-4.1 -t 50 -p "Discuss philosophy"
        
        # Using dimensional prompts with name choosing
        pidgin chat -d peers:science --choose-names
        
        # List all available models
        pidgin models --detailed
    
    For more information on a command: pidgin COMMAND --help
    """
    if config:
        create_config_templates()
    elif ctx.invoked_subcommand is None:
        # Show help if no command provided
        click.echo(ctx.get_help())


@cli.command()
@click.help_option("-h", "--help")
@click.option("-a", "--model-a", default="claude", 
              help="First model - e.g., claude, opus, gpt, haiku")
@click.option(
    "-b", "--model-b", default="claude", 
    help="Second model - e.g., gpt-4.1, gemini, grok"
)
@click.option(
    "-t", "--turns", default=10, 
    help="Number of conversation turns (default: 10, recommended: 20-100)"
)
@click.option("-p", "--prompt", 
              help="Initial prompt to start conversation - sets the topic and tone")
@click.option("-d", "--dimensions", 
              help="Use dimensional prompt system - e.g., 'peers:philosophy' or 'debate:science:analytical'")
@click.option("--puzzle", help="Specific puzzle name for puzzles topic")
@click.option("--experiment", help="Specific thought experiment name")
@click.option("--topic-content", help="Custom content for puzzles/experiments")
@click.option("-s", "--save-to", help="Save transcript to specific location")
@click.option(
    "-c", "--config", type=click.Path(exists=True), help="Path to config file"
)
@click.option(
    "-n",
    "--no-attractor-detection",
    "--no-detection",
    is_flag=True,
    help="Disable attractor detection",
)
@click.option(
    "-m",
    "--manual",
    is_flag=True,
    help="Enable manual mode (approve each message step-by-step)",
)
@click.option(
    "--convergence-threshold",
    type=click.FloatRange(0.0, 1.0),
    default=0.75,
    help="Convergence warning threshold (default: 0.75)",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(),
    help="Output directory for conversations (default: ./pidgin_output)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show all events and chunks (verbose mode)",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Minimal output (quiet mode)",
)
@click.option(
    "--timing",
    is_flag=True,
    help="Show timing information",
)
@click.option(
    "--choose-names",
    is_flag=True,
    help="Let agents choose their own names",
)
@click.option(
    "--stability",
    type=click.IntRange(0, 4),
    default=2,
    help="System prompt stability level (0=chaos, 2=default, 4=max)",
)
@click.option(
    "--show-system-prompts",
    is_flag=True,
    help="Display system prompts at start",
)
def chat(
    model_a,
    model_b,
    turns,
    prompt,
    dimensions,
    puzzle,
    experiment,
    topic_content,
    save_to,
    config,
    no_attractor_detection,
    manual,
    convergence_threshold,
    output_dir,
    verbose,
    quiet,
    timing,
    choose_names,
    stability,
    show_system_prompts,
):
    """Run a conversation between two AI agents.
    
    This command starts a conversation that will run for the specified number of turns.
    The conversation is saved to ./pidgin_output/ with full event logs and transcripts.
    
    EXAMPLES:
    
    Basic conversation (10 turns):
        pidgin chat -a claude -b gpt
    
    Longer philosophical discussion:
        pidgin chat -a opus -b gpt-4.1 -t 50 -p "What is consciousness?"
    
    Using dimensional prompts:
        pidgin chat -d debate:philosophy:analytical
    
    Let agents choose names:
        pidgin chat -a haiku -b nano --choose-names
    
    Verbose mode with timing:
        pidgin chat -a claude -b claude -v --timing
    
    INTERRUPT CONTROL:
        Press Ctrl+C at any time to pause the conversation.
        You can then choose to continue or exit gracefully.
    
    OUTPUT:
        All conversations are saved to ./pidgin_output/conversations/YYYY-MM-DD/
        Each conversation includes:
        • events.jsonl - Complete event log
        • conversation.json - Structured data with metrics
        • conversation.md - Human-readable transcript
    """
    from .event_bus import EventBus
    from .event_logger import EventLogger
    from .conductor import Conductor
    from .providers.event_wrapper import EventAwareProvider
    from .output_manager import OutputManager

    # Build initial prompt from dimensions and/or custom prompt
    initial_prompt = _build_initial_prompt(
        prompt, dimensions, puzzle, experiment, topic_content
    )
    if not initial_prompt:
        initial_prompt = "Hello! I'm looking forward to our conversation."

    # Determine display mode
    if quiet:
        display_mode = "quiet"
    elif verbose:
        display_mode = "verbose"
    else:
        display_mode = "normal"

    # Create output manager
    output_manager = OutputManager(output_dir)  # Uses output_dir if provided

    # Get model configs
    try:
        config_a = get_model_config(model_a)
        config_b = get_model_config(model_b)
        model_a_id = config_a.model_id if config_a else model_a
        model_b_id = config_b.model_id if config_b else model_b
    except ValueError as e:
        console.print(f"[red]Model error: {e}[/red]")
        return

    # Create providers
    try:
        providers_map = {
            "agent_a": get_provider_for_model(model_a),
            "agent_b": get_provider_for_model(model_b),
        }
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    # Create event-driven CONDUCTOR with output manager
    conductor = Conductor(providers_map, output_manager, console)

    # Create agents
    agent_a_obj = Agent(id="agent_a", model=model_a_id)
    agent_b_obj = Agent(id="agent_b", model=model_b_id)

    # Show system prompts if requested
    if show_system_prompts:
        from .system_prompts import get_system_prompts, get_preset_info
        system_prompts = get_system_prompts(
            stability_level=stability,
            choose_names=choose_names
        )
        preset_info = get_preset_info(stability)
        
        console.print(f"\n[bold cyan]System Prompts:[/bold cyan]")
        console.print(f"Stability Level: {stability} ({preset_info['name']})")
        console.print(f"Description: {preset_info['description']}\n")
        
        if system_prompts["agent_a"]:
            console.print(Panel(
                system_prompts["agent_a"],
                title="System Prompt - Agent A",
                border_style="green"
            ))
        else:
            console.print("[dim]Agent A: No system prompt (chaos mode)[/dim]")
            
        if system_prompts["agent_b"]:
            console.print(Panel(
                system_prompts["agent_b"],
                title="System Prompt - Agent B",
                border_style="blue"
            ))
        else:
            console.print("[dim]Agent B: No system prompt (chaos mode)[/dim]")
        console.print()

    # Display EVENT-DRIVEN configuration (only in verbose mode)
    if verbose:
        console.print(
            Panel(
                f"[bold green]🎭 EVENT-DRIVEN CONVERSATION[/bold green]\n"
                f"Model A: {model_a_id}\n"
                f"Model B: {model_b_id}\n"
                f"Max turns: {turns}\n"
                f"Initial prompt: {initial_prompt[:50]}...\n\n"
                f"[yellow]All events will be displayed in real-time![/yellow]",
                title="Event System Active",
                border_style="green",
            )
        )

    # Run the conversation
    try:
        conversation = asyncio.run(
            conductor.run_conversation(
                agent_a=agent_a_obj,
                agent_b=agent_b_obj,
                initial_prompt=initial_prompt,
                max_turns=turns,
                display_mode=display_mode,
                show_timing=timing,
                choose_names=choose_names,
                stability_level=stability,
            )
        )

        console.print("\n[bold green]Conversation completed![/bold green]")
        console.print(f"Total messages: {len(conversation.messages)}")
        console.print(f"Conversation ID: {conversation.id}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Conversation interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


@cli.command()
@click.help_option("-h", "--help")
@click.option("-p", "--provider", help="Filter by provider (anthropic/openai/google/xai)")
@click.option("-d", "--detailed", is_flag=True, help="Show detailed model information")
def models(provider, detailed):
    """List available AI models and their capabilities.
    
    Shows all models that can be used in conversations, including their context
    windows, pricing tiers, and recommended pairings.
    
    EXAMPLES:
    
    List all models:
        pidgin models
    
    Show detailed information:
        pidgin models --detailed
    
    Filter by provider:
        pidgin models --provider anthropic
    
    MODEL SHORTCUTS:
        Many models have convenient shortcuts:
        • claude → claude-4-sonnet-20250514
        • gpt → gpt-4o
        • opus → claude-4-opus-20250514
        • haiku → claude-3-5-haiku-20241022
    
    Use any model ID or shortcut in the chat command.
    """

    if provider:
        # Filter by provider
        if provider.lower() not in ["anthropic", "openai", "google", "xai"]:
            console.print(
                f"[red]Error: Invalid provider '{provider}'. Use 'anthropic', 'openai', 'google', or 'xai'.[/red]"
            )
            return
        models_to_show = get_models_by_provider(provider.lower())
        console.print(f"\n[bold]Available {provider.upper()} Models:[/bold]\n")
    else:
        # Show all models
        console.print("\n[bold]Available Models:[/bold]\n")
        models_to_show = list(MODELS.values())

    # Group by provider if showing all
    if not provider:
        # Anthropic models
        console.print("[cyan]ANTHROPIC:[/cyan]")
        anthropic_models = [m for m in models_to_show if m.provider == "anthropic"]
        _display_models(anthropic_models, detailed)

        console.print("\n[cyan]OPENAI:[/cyan]")
        openai_models = [m for m in models_to_show if m.provider == "openai"]
        _display_models(openai_models, detailed)

        console.print("\n[cyan]GOOGLE:[/cyan]")
        google_models = [m for m in models_to_show if m.provider == "google"]
        _display_models(google_models, detailed)

        console.print("\n[cyan]XAI:[/cyan]")
        xai_models = [m for m in models_to_show if m.provider == "xai"]
        _display_models(xai_models, detailed)
    else:
        _display_models(models_to_show, detailed)

    console.print("\n[dim]Use any model ID or alias in conversations.[/dim]")
    console.print("[dim]Example: pidgin chat --agent-a haiku --agent-b gpt[/dim]\n")


def _display_models(models, detailed):
    """Display models in a formatted table"""
    if detailed:
        # Detailed table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Model ID", style="green")
        table.add_column("Aliases", style="yellow")
        table.add_column("Context", style="cyan")
        table.add_column("Tier", style="blue")
        table.add_column("Style", style="magenta")
        table.add_column("Notes")

        for model in models:
            aliases = ", ".join(model.aliases[:3])  # Show first 3 aliases
            if len(model.aliases) > 3:
                aliases += f" (+{len(model.aliases)-3} more)"

            context = f"{model.context_window:,}" if model.context_window > 0 else "N/A"
            notes = model.notes or ""
            if model.deprecated:
                notes = f"[red]DEPRECATED {model.deprecation_date}[/red] {notes}"

            table.add_row(
                model.model_id,
                aliases,
                context,
                model.pricing_tier,
                model.characteristics.conversation_style,
                notes,
            )
    else:
        # Simple table format
        table = Table(show_header=True, header_style="bold blue", show_lines=False)
        table.add_column("Model", style="green", min_width=25, max_width=30)
        table.add_column("Aliases", style="dim", max_width=30)
        table.add_column("Context", justify="right", style="cyan", min_width=7)
        table.add_column("Notes", style="dim", max_width=40)

        for model in models:
            # Format aliases (limit to 3 most important)
            aliases = model.aliases[:3]  # Take first 3 aliases
            aliases_str = ", ".join(aliases)
            if len(model.aliases) > 3:
                aliases_str += f", +{len(model.aliases)-3}"

            # Format context window
            context = (
                f"{model.context_window//1000}K" if model.context_window > 0 else "–"
            )

            # Format notes
            notes = model.notes or ""
            if model.deprecated:
                notes = f"⚠️ DEPRECATED {model.deprecation_date}"

            table.add_row(model.model_id, aliases_str, context, notes)

    console.print(table)


@cli.command()
@click.help_option("-h", "--help")
def resume():
    """Resume conversations by replaying events (coming soon)."""
    console.print("[yellow]Event replay coming in a future release![/yellow]")
    console.print("For now, conversations run to completion or exit.")
    
    # Future: Event replay will enable resume by replaying events.jsonl
    # No need for separate checkpoint files - events ARE the state.


@cli.command()
@click.help_option("-h", "--help")
@click.option("--example", help="Show example for specific dimension combination")
@click.option("--list", "list_only", is_flag=True, help="List just dimension names")
@click.option("--detailed", is_flag=True, help="Show detailed info about a dimension")
@click.argument("dimension", required=False)
def dimensions(example, list_only, detailed, dimension):
    """Explore dimensional prompt system for conversation setup.
    
    Dimensional prompts let you quickly configure conversation dynamics by
    combining different aspects like context (peers/debate/teaching) and
    topics (philosophy/science/language).
    
    FORMAT:
        -d context:topic[:mode]
    
    EXAMPLES:
    
    List all dimensions:
        pidgin dimensions
    
    Show specific dimension:
        pidgin dimensions context --detailed
    
    See example output:
        pidgin dimensions --example peers:philosophy
    
    QUICK COMBINATIONS:
        • peers:philosophy → Collaborative philosophical discussion
        • debate:science:analytical → Analytical scientific debate
        • teaching:puzzles --puzzle riddle → Teaching session about riddles
    
    SPECIAL TOPICS:
        Some topics require additional parameters:
        • puzzles: Use --puzzle to specify which puzzle
        • thought_experiments: Use --experiment to specify which one
    """
    generator = DimensionalPromptGenerator()

    if example:
        # Show example for specific combination
        try:
            prompt = generator.generate(example)
            console.print(f"\n[bold]Example for '{example}':[/bold]")
            console.print(f'"{prompt}"\n')
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
        return

    if dimension and detailed:
        # Show detailed info about a specific dimension
        console.print()
        console.print(generator.describe_dimension(dimension))
        console.print()
        return

    if list_only:
        # Just list dimension names
        all_dims = generator.get_all_dimensions()
        console.print("\n[bold]Available dimensions:[/bold]")
        for dim_name in all_dims:
            console.print(f"  • {dim_name}")
        console.print()
        return

    # Default: show all dimensions and their values
    console.print("\n[bold]Dimensional Prompt System[/bold]\n")
    console.print("Create prompts by combining dimensions with colons:")
    console.print("  pidgin chat -d context:topic[:mode][:energy][:formality]\n")

    all_dims = generator.get_all_dimensions()

    for dim_name, dim in all_dims.items():
        console.print(f"[bold cyan]{dim_name.upper()}[/bold cyan] - {dim.description}")
        console.print(f"  Required: {'Yes' if dim.required else 'No'}")
        console.print("  Values:")

        for value, desc in dim.values.items():
            if desc == "[SPECIAL]":
                console.print(
                    f"    • [yellow]{value}[/yellow] - Requires additional content"
                )
            else:
                # Truncate long descriptions
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                console.print(f"    • [green]{value}[/green] - {desc}")
        console.print()

    # Show examples
    console.print("[bold]Examples:[/bold]")
    examples = [
        ("peers:philosophy", "Collaborative philosophical discussion"),
        ("debate:science:analytical", "Analytical debate about science"),
        ("teaching:puzzles --puzzle towel", "Teaching session about a specific puzzle"),
        (
            "interview:meta:exploratory",
            "Exploratory interview about the conversation itself",
        ),
        (
            "collaboration:thought_experiments --experiment trolley_problem",
            "Work together on the trolley problem",
        ),
    ]

    for example_spec, description in examples:
        from rich.text import Text

        example_text = Text()
        example_text.append("  pidgin chat -d ", style="dim")
        example_text.append(example_spec, style="dim")
        console.print(example_text)
        console.print(f"    → {description}")
    console.print()


@cli.command()
def about():
    """Learn more about Pidgin and its research goals.
    
    Displays information about the project, its scientific approach,
    and how to contribute to the research.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.text import Text
    
    console = Console()
    
    # Create a fancy header
    header = Text()
    header.append("🧪 ", style="bold")
    header.append("About Pidgin", style="bold #8fbcbb")
    header.append(" 🧪", style="bold")
    
    # Main content with better formatting
    about_content = """
[bold cyan]Pidgin[/bold cyan] is a research tool for studying AI-to-AI communication patterns.

## [bold green]What We're Studying[/bold green]

• [bold]Convergence[/bold]: How AI agents align their communication styles
• [bold]Patterns[/bold]: What structures emerge in extended conversations  
• [bold]Dynamics[/bold]: How different model pairs interact
• [bold]Interventions[/bold]: How human input affects conversations

## [bold yellow]Scientific Approach[/bold yellow]

We make [bold red]no assumptions[/bold red] about what we'll find. Pidgin:
• Records [italic]every event[/italic] in conversations
• Measures convergence between agents
• Looks for patterns ([dim]without assuming they exist[/dim])
• Provides reproducible experiments

## [bold blue]Output Data[/bold blue]

Each conversation produces:
• Complete [green]event logs[/green] for analysis
• Convergence metrics over time
• Structured [blue]JSON[/blue] for data science
• Human-readable [yellow]transcripts[/yellow]

## [bold magenta]Contributing[/bold magenta]

This is [bold]alpha software[/bold] for research purposes.
GitHub: [link=https://github.com/tommygun/pidgin]https://github.com/tommygun/pidgin[/link]

---

[bold italic #5e81ac]No claims, just observation.[/bold italic #5e81ac]

We're building tools to discover what happens when AIs talk,
not assuming we already know.
    """
    
    # Create a status table
    status_table = Table(show_header=True, header_style="bold cyan", border_style="#5e81ac")
    status_table.add_column("Feature", style="white")
    status_table.add_column("Status", justify="center")
    
    status_table.add_row("Event Architecture", "[bold green]✓ Working[/bold green]")
    status_table.add_row("Pause/Resume", "[bold green]✓ Working[/bold green]")
    status_table.add_row("Multi-Provider", "[bold green]✓ Working[/bold green]")
    status_table.add_row("Convergence Display", "[yellow]⚡ Partial[/yellow]")
    status_table.add_row("Context Warnings", "[yellow]⚡ Partial[/yellow]")
    status_table.add_row("Batch Experiments", "[red]✗ Planned[/red]")
    
    # Print everything with nice layout
    console.print()
    console.print(header, justify="center")
    console.print()
    console.print(about_content)
    console.print()
    console.print(Panel(status_table, title="[bold]Current Status[/bold]", border_style="#5e81ac"))
    console.print()


if __name__ == "__main__":
    cli()
