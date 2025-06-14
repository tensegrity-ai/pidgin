import click
import asyncio
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .models import MODELS, get_model_config, get_models_by_provider
from .types import Agent
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.google import GoogleProvider
from .providers.xai import xAIProvider
from .router import DirectRouter
from .dialogue import DialogueEngine
from .transcripts import TranscriptManager
from .checkpoint import ConversationState, CheckpointManager
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
        from rich.text import Text

        console = Console()
        title = Text("PIDGIN", style="bold cyan")
        subtitle = Text("AI Conversation Research Tool", style="dim")
        tagline = Text(
            "Where language models meet, talk, and sometimes argue...",
            style="italic dim",
        )

        console.print()
        console.print(title, justify="left")
        console.print(subtitle, justify="left")
        console.print(tagline, justify="left")
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
    """Pidgin - AI conversation research tool"""
    if config:
        create_config_templates()
    elif ctx.invoked_subcommand is None:
        # Show help if no command provided
        click.echo(ctx.get_help())


@cli.command()
@click.help_option("-h", "--help")
@click.option("-a", "--model-a", default="claude", help="First model (default: claude)")
@click.option(
    "-b", "--model-b", default="claude", help="Second model (default: claude)"
)
@click.option(
    "-t", "--turns", default=10, help="Number of conversation turns (default: 10)"
)
@click.option("-p", "--prompt", help="Custom initial prompt")
@click.option("-d", "--dimensions", help="Dimensional prompt (e.g., peers:philosophy)")
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
):
    """Run a conversation between two AI agents"""

    # Resolve model shortcuts using the new system
    config_a = get_model_config(model_a)
    config_b = get_model_config(model_b)

    model_a_id = config_a.model_id if config_a else model_a
    model_b_id = config_b.model_id if config_b else model_b

    # Build initial prompt from dimensions and/or custom prompt
    initial_prompt = _build_initial_prompt(
        prompt, dimensions, puzzle, experiment, topic_content
    )

    # Create agents
    agents = {
        "agent_a": Agent(id="agent_a", model=model_a_id),
        "agent_b": Agent(id="agent_b", model=model_b_id),
    }

    # Create providers based on model type
    try:
        providers = {
            "agent_a": get_provider_for_model(model_a_id),
            "agent_b": get_provider_for_model(model_b_id),
        }
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    # Load configuration
    if config:
        cfg = load_config(Path(config))
    else:
        cfg = Config()

    # Override attractor detection if requested
    if no_attractor_detection:
        cfg.set("conversation.attractor_detection.enabled", False)

    # Setup components
    router = DirectRouter(providers)
    transcript_manager = TranscriptManager(save_to)
    engine = DialogueEngine(router, transcript_manager, cfg)

    # Display configuration
    console.print(f"[bold]🤖 Starting conversation: {model_a_id} ↔ {model_b_id}[/bold]")
    console.print(
        f"[dim]📝 Initial prompt: {initial_prompt[:50]}{'...' if len(initial_prompt) > 50 else ''}[/dim]"
    )
    console.print(f"[dim]🔄 Max turns: {turns}[/dim]")

    # Show context management status
    context_enabled = (
        cfg.get("context_management.enabled", True) if hasattr(cfg, "get") else True
    )
    if context_enabled:
        console.print(f"[dim]📏 Context tracking: [green]ON[/green][/dim]")
    else:
        console.print(f"[dim]📏 Context tracking: [red]OFF[/red][/dim]")

    # Show attractor detection status
    detection_enabled = (
        cfg.get("conversation.attractor_detection.enabled", True)
        if hasattr(cfg, "get")
        else True
    )
    if detection_enabled:
        threshold = (
            cfg.get("conversation.attractor_detection.threshold", 3)
            if hasattr(cfg, "get")
            else 3
        )
        window = (
            cfg.get("conversation.attractor_detection.window_size", 10)
            if hasattr(cfg, "get")
            else 10
        )
        console.print(
            f"[dim]🔍 Attractor detection: [green]ON[/green] (threshold: {threshold}, window: {window})[/dim]"
        )
    else:
        console.print(f"[dim]🔍 Attractor detection: [red]OFF[/red][/dim]")

    # Show mode (default is flowing conductor)
    if manual:
        console.print(
            f"[dim]🎼 Mode: [green]MANUAL[/green] (message-by-message approval)[/dim]"
        )
    else:
        console.print(
            f"[dim]🎼 Mode: [green]FLOWING[/green] (default - press Ctrl+C to pause)[/dim]"
        )

    # Show convergence tracking
    console.print(
        f"[dim]📊 Convergence tracking: [green]ON[/green] (warning at {convergence_threshold:.2f})[/dim]"
    )

    console.rule(style="dim")
    console.print()

    try:
        asyncio.run(
            engine.run_conversation(
                agents["agent_a"],
                agents["agent_b"],
                initial_prompt,
                turns,
                manual_mode=manual,
                convergence_threshold=convergence_threshold,
            )
        )

        # Success exit message
        console.print()
        completion_content = "[green]✅ CONVERSATION COMPLETE[/green]\n"
        completion_content += "📁 Transcript saved successfully\n"

        # Check if attractor was detected
        if hasattr(engine, "attractor_detected") and engine.attractor_detected:
            result = engine.attractor_detected
            completion_content += f"🎯 Attractor detected: {result['type']} at turn {result['turn_detected']}"
        else:
            completion_content += "🎯 All turns completed normally"

        console.print(
            Panel(
                completion_content,
                title="[bold green]Conversation Summary[/bold green]",
                border_style="green",
            )
        )
        console.print()

    except KeyboardInterrupt:
        # Interrupted exit message
        console.print()
        stopped_content = "[yellow]⏹️  CONVERSATION STOPPED[/yellow]\n"
        stopped_content += "📁 Transcript saved (partial conversation)\n"
        stopped_content += "🛑 Stopped by user (Ctrl+C)"

        console.print(
            Panel(
                stopped_content,
                title="[bold yellow]Conversation Interrupted[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print()

    except Exception as e:
        # Error exit message
        console.print()
        error_content = "[red]❌ CONVERSATION ERROR[/red]\n"
        error_content += f"💥 Error: {e}\n"
        error_content += "📁 Transcript may be incomplete"

        console.print(
            Panel(
                error_content,
                title="[bold red]Conversation Error[/bold red]",
                border_style="red",
            )
        )
        console.print()


@cli.command()
@click.help_option("-h", "--help")
@click.option("-p", "--provider", help="Filter by provider (anthropic/openai)")
@click.option("-d", "--detailed", is_flag=True, help="Show detailed information")
def models(provider, detailed):
    """List all available models and their shortcuts"""

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
@click.argument("checkpoint_file", required=False, type=click.Path(exists=True))
@click.option("-l", "--latest", is_flag=True, help="Resume from the latest checkpoint")
@click.option(
    "-c",
    "--convergence-threshold",
    type=click.FloatRange(0.0, 1.0),
    help="Override convergence warning threshold (0.0-1.0)",
)
@click.option(
    "-t",
    "--additional-turns",
    type=click.IntRange(1, 1000),
    help="Add extra turns beyond original max_turns",
)
def resume(checkpoint_file, latest, convergence_threshold, additional_turns):
    """Resume a paused conversation from checkpoint"""

    # Use the standard pidgin data directory for checkpoints
    pidgin_data_dir = Path.home() / ".pidgin_data"
    checkpoint_manager = CheckpointManager(pidgin_data_dir)

    # Determine which checkpoint to use
    if latest:
        checkpoint_path = checkpoint_manager.find_latest_checkpoint()
        if not checkpoint_path:
            console.print("[red]No checkpoints found[/red]")
            return
    elif checkpoint_file:
        checkpoint_path = Path(checkpoint_file)
    else:
        # List available checkpoints
        checkpoints = checkpoint_manager.list_checkpoints()
        if not checkpoints:
            console.print("[red]No checkpoints found[/red]")
            console.print("[dim]Use 'pidgin chat' to start a new conversation[/dim]")
            return

        console.print("\n[bold]Available checkpoints:[/bold]\n")
        for i, cp in enumerate(checkpoints[:10]):  # Show max 10
            if "error" in cp:
                console.print(f"{i+1}. [red]{cp['path']} (Error: {cp['error']})[/red]")
            else:
                console.print(f"{i+1}. {cp['path']}")
                console.print(
                    f"   [dim]Models: {cp['model_a']} vs {cp['model_b']}[/dim]"
                )
                console.print(
                    f"   [dim]Turn {cp['turn_count']}/{cp['max_turns']} - {cp['remaining_turns']} turns remaining[/dim]"
                )
                console.print(f"   [dim]Paused: {cp['pause_time']}[/dim]\n")

        console.print("[yellow]Specify a checkpoint file or use --latest[/yellow]")
        return

    # Load checkpoint
    try:
        state = ConversationState.load_checkpoint(checkpoint_path)
        info = state.get_resume_info()

        # Apply modifications if specified
        original_max_turns = state.max_turns
        final_max_turns = state.max_turns

        if additional_turns:
            final_max_turns = state.max_turns + additional_turns
            state.max_turns = final_max_turns
            console.print(
                f"[yellow]Added {additional_turns} extra turns (was {original_max_turns}, now {final_max_turns})[/yellow]"
            )

        # Set convergence threshold for display
        threshold_msg = ""
        if convergence_threshold is not None:
            threshold_msg = (
                f" [dim](convergence threshold: {convergence_threshold:.2f})[/dim]"
            )

        console.print(f"\n[bold]Resuming conversation:{threshold_msg}[/bold]")
        console.print(f"Models: {info['model_a']} vs {info['model_b']}")
        console.print(f"Turn: {info['turn_count']}/{final_max_turns}")

        # Update remaining turns calculation
        remaining = final_max_turns - info["turn_count"]
        console.print(f"Remaining turns: {remaining}\n")

        # Recreate agents and providers
        agents = {
            "agent_a": Agent(id=state.agent_a_id, model=state.model_a),
            "agent_b": Agent(id=state.agent_b_id, model=state.model_b),
        }

        providers = {
            "agent_a": get_provider_for_model(state.model_a),
            "agent_b": get_provider_for_model(state.model_b),
        }

        # Setup components
        router = DirectRouter(providers)
        transcript_manager = TranscriptManager()

        # Load config
        cfg = Config()

        engine = DialogueEngine(router, transcript_manager, cfg)

        # Prepare run_conversation arguments
        run_args = {
            "agent_a": agents["agent_a"],
            "agent_b": agents["agent_b"],
            "initial_prompt": state.initial_prompt,
            "max_turns": final_max_turns,
            "resume_from_state": state,
        }

        # Add convergence threshold if specified
        if convergence_threshold is not None:
            run_args["convergence_threshold"] = convergence_threshold

        # Resume conversation
        asyncio.run(engine.run_conversation(**run_args))

        # Resume success message
        console.print()
        console.rule("[green]✅ RESUMED CONVERSATION COMPLETE[/green]", style="green")
        console.print("[green]📁 Transcript updated successfully[/green]")
        console.print("[green]🔄 Conversation resumed and finished[/green]")
        console.rule(style="green")
        console.print()

    except FileNotFoundError:
        # File not found error
        console.print()
        console.rule("[red]❌ CHECKPOINT NOT FOUND[/red]", style="red")
        console.print(f"[red]📂 File: {checkpoint_path}[/red]")
        console.print("[red]💡 Use 'pidgin resume' to list available checkpoints[/red]")
        console.rule(style="red")
        console.print()

    except Exception as e:
        # General resume error
        console.print()
        console.rule("[red]❌ RESUME ERROR[/red]", style="red")
        console.print(f"[red]💥 Error: {e}[/red]")
        console.print("[red]🔧 Try checking the checkpoint file format[/red]")
        console.rule(style="red")
        console.print()


@cli.command()
@click.help_option("-h", "--help")
@click.option("--example", help="Show example for specific dimension combination")
@click.option("--list", "list_only", is_flag=True, help="List just dimension names")
@click.option("--detailed", is_flag=True, help="Show detailed info about a dimension")
@click.argument("dimension", required=False)
def dimensions(example, list_only, detailed, dimension):
    """Explore available dimensional prompts"""
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


@cli.command(name="chat-events")
@click.help_option("-h", "--help")
@click.option("-a", "--model-a", default="claude", help="First model (default: claude)")
@click.option("-b", "--model-b", default="gpt", help="Second model (default: gpt)")
@click.option("-p", "--prompt", help="Initial prompt for conversation")
@click.option("-t", "--turns", default=5, help="Maximum number of turns (default: 5)")
def chat_events(model_a, model_b, prompt, turns):
    """Run a conversation using the new event-driven architecture.
    
    This command demonstrates the event system with full transparency.
    Every action and decision is visible as events flow through the system.
    """
    from .event_bus import EventBus
    from .event_logger import EventLogger
    from .conductor import Conductor
    from .providers.event_wrapper import EventAwareProvider
    
    # Default prompt
    if not prompt:
        prompt = "Hello! I'm looking forward to our conversation."
    
    # Initialize event system
    bus = EventBus()
    logger = EventLogger(bus, console)
    
    # Get model configs
    try:
        model_a_config = get_model_config(model_a)
        model_b_config = get_model_config(model_b)
        model_a_full = model_a_config.model_id if model_a_config else model_a
        model_b_full = model_b_config.model_id if model_b_config else model_b
    except ValueError as e:
        console.print(f"[red]Model error: {e}[/red]")
        raise click.Abort()
    
    # Create providers
    providers_map = {
        "agent_a": get_provider_for_model(model_a),
        "agent_b": get_provider_for_model(model_b),
    }
    
    # Wrap providers with event awareness
    wrapped_providers = {
        agent_id: EventAwareProvider(provider, bus, agent_id)
        for agent_id, provider in providers_map.items()
    }
    
    # Create conductor
    conductor = Conductor(bus, wrapped_providers)
    
    # Create agents
    agent_a_obj = Agent(id="agent_a", model=model_a_full)
    agent_b_obj = Agent(id="agent_b", model=model_b_full)
    
    # Run conversation
    console.print(
        Panel(
            "[bold green]Starting Event-Driven Conversation[/bold green]\n"
            f"Model A: {model_a_full}\n"
            f"Model B: {model_b_full}\n"
            f"Max turns: {turns}\n\n"
            "[yellow]All events will be displayed below...[/yellow]",
            title="🎭 Event System Demo",
            border_style="green"
        )
    )
    
    try:
        conversation = asyncio.run(
            conductor.run_conversation(
                agent_a=agent_a_obj,
                agent_b=agent_b_obj,
                initial_prompt=prompt,
                max_turns=turns,
            )
        )
        
        console.print("\n[bold green]Conversation completed![/bold green]")
        console.print(f"Total messages: {len(conversation.messages)}")
        console.print(f"Event history: {len(bus.get_history())} events")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    cli()
