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
from .config.models import MODELS, get_model_config, get_models_by_provider
from .core.types import Agent, Conversation
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.google import GoogleProvider
from .providers.xai import xAIProvider
from .config.config import Config, load_config
from .config.dimensional_prompts import DimensionalPromptGenerator

console = Console()


def _build_initial_prompt(
    custom_prompt: Optional[str],
    dimensions: Optional[str],
) -> str:
    """Build initial prompt from custom prompt and/or dimensions.
    
    Args:
        custom_prompt: Either a string or path to .md file
        dimensions: Dimensional prompt specification
    """
    parts = []
    
    # Handle dimensional prompt if specified
    if dimensions:
        try:
            generator = DimensionalPromptGenerator()
            
            # Check if we need to handle custom prompt integration
            if custom_prompt:
                # Parse dimensions to check if it's a regular topic
                dim_parts = dimensions.split(':')
                if len(dim_parts) >= 2:
                    topic = dim_parts[1]
                    
                    # Check if it's a file
                    if custom_prompt.endswith('.md') and os.path.exists(custom_prompt):
                        # Read file content
                        try:
                            with open(custom_prompt, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                            if not content:
                                console.print(f"[#ebcb8b]Warning: File '{custom_prompt}' is empty[/#ebcb8b]")
                            
                            # Generate dimensional prompt with placeholder
                            dimensional_prompt = generator.generate(dimensions)
                            # Replace {topic} with transition phrase
                            dimensional_prompt = dimensional_prompt.replace(
                                generator.TOPIC_DIMENSION.values[topic],
                                "the following scenario"
                            )
                            parts.append(dimensional_prompt)
                            parts.append("\n\n" + content)
                        except IOError as e:
                            console.print(f"[#bf616a]Error reading file '{custom_prompt}': {e}[/#bf616a]")
                            raise click.Abort()
                        except UnicodeDecodeError:
                            console.print(f"[#bf616a]Error: File '{custom_prompt}' is not valid UTF-8 text[/#bf616a]")
                            raise click.Abort()
                    else:
                        # It's a string
                        if custom_prompt.endswith('.md') and not os.path.exists(custom_prompt):
                            console.print(f"[#bf616a]Error: File '{custom_prompt}' not found[/#bf616a]")
                            raise click.Abort()
                        
                        # For strings, replace {topic} with the custom prompt
                        dimensional_prompt = generator.generate(dimensions)
                        # Replace the topic value with custom prompt
                        dimensional_prompt = dimensional_prompt.replace(
                            generator.TOPIC_DIMENSION.values[topic],
                            custom_prompt
                        )
                        parts.append(dimensional_prompt)
                else:
                    # Invalid dimension format, just generate normally
                    dimensional_prompt = generator.generate(dimensions)
                    parts.append(dimensional_prompt)
                    parts.append(custom_prompt)
            else:
                # No custom prompt provided
                dimensional_prompt = generator.generate(dimensions)
                parts.append(dimensional_prompt)
        except ValueError as e:
            console.print(f"[#bf616a]Error in dimensional prompt: {e}[/#bf616a]")
            raise click.Abort()
    else:
        # No dimensional prompt, just use custom prompt if provided
        if custom_prompt:
            # Check if it's a file path
            if custom_prompt.endswith('.md') and os.path.exists(custom_prompt):
                try:
                    with open(custom_prompt, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if not content:
                        console.print(f"[#ebcb8b]Warning: File '{custom_prompt}' is empty[/#ebcb8b]")
                    parts.append(content)
                except IOError as e:
                    console.print(f"[#bf616a]Error reading file '{custom_prompt}': {e}[/#bf616a]")
                    raise click.Abort()
                except UnicodeDecodeError:
                    console.print(f"[#bf616a]Error: File '{custom_prompt}' is not valid UTF-8 text[/#bf616a]")
                    raise click.Abort()
            else:
                # It's a string
                if custom_prompt.endswith('.md') and not os.path.exists(custom_prompt):
                    console.print(f"[#bf616a]Error: File '{custom_prompt}' not found[/#bf616a]")
                    raise click.Abort()
                parts.append(custom_prompt)
    
    # If nothing specified, use default
    if not parts:
        return "Hello! I'm looking forward to our conversation."
    
    # Combine parts
    return " ".join(parts) if all(isinstance(p, str) for p in parts) else "".join(str(p) for p in parts)


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
        raise ValueError(f"Unknown model provider for: {model}")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli():
    """AI conversation research tool for studying emergent communication patterns.

    Pidgin enables controlled experiments between AI agents to discover how they
    develop communication patterns, convergence behaviors, and linguistic adaptations.

    [bold]QUICK START:[/bold]
    pidgin chat -a claude -b gpt -t 20

    [bold]EXAMPLES:[/bold]

    [#4c566a]Basic conversation with custom prompt:[/#4c566a]
        pidgin chat -a opus -b gpt-4.1 -t 50 -p "Discuss philosophy"

    [#4c566a]Using dimensional prompts:[/#4c566a]
        pidgin chat -a claude -b gpt -d peers:philosophy:analytical

    [#4c566a]Let agents choose names:[/#4c566a]
        pidgin chat -a claude -b gpt --choose-names

    [#4c566a]High convergence monitoring:[/#4c566a]
        pidgin chat -a claude -b gpt -t 100 --convergence-threshold 0.8

    [bold]CONFIGURATION:[/bold]

    • Configuration files: ~/.pidgin/ or ./.pidgin/
    • Create templates: pidgin init
    """
    pass


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
def init():
    """Initialize configuration directory with template files.

    Creates a .pidgin/ directory in your current folder with template
    configuration files for:

    • Custom dimensions (planned)

    After running this command, edit the YAML files to add your own content.
    """
    config_dir = Path.cwd() / ".pidgin"
    created_files = []
    
    # Create directory
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
        console.print(f"Created directory: {config_dir}")
    

    # Dimensions template
    dim_path = config_dir / "dimensions.yaml"
    if not dim_path.exists():
        from datetime import datetime
        dim_content = f"""# Pidgin Custom Dimensions
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# Define custom dimensions for prompt generation.
# (This feature is planned for future releases)
#
# For now, use the built-in dimensions:
#   Context: peers, teaching, debate, interview, collaboration, neutral
#   Topic: philosophy, language, science, creativity, meta
#   Mode: analytical, intuitive, exploratory, focused

dimensions:
  # Future feature - custom dimensions will go here
"""
        with open(dim_path, "w") as f:
            f.write(dim_content)
        created_files.append(dim_path)
    
    # Report results
    if created_files:
        console.print("\n[bold green]✓ Configuration templates created:[/bold green]")
        for file in created_files:
            console.print(f"  • {file.relative_to(Path.cwd())}")
        console.print("\n[#4c566a]Edit these files to add your own content.[/#4c566a]")
    else:
        console.print("[yellow]All configuration files already exist.[/yellow]")
        console.print(f"[#4c566a]Check {config_dir.relative_to(Path.cwd())}/[/#4c566a]")


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
def models():
    """Display available AI models organized by provider.

    Shows all supported models with their aliases, context windows,
    and key characteristics.
    """
    table = Table(title="Available Models", show_header=True, header_style="bold")
    table.add_column("Provider", style="cyan", width=12)
    table.add_column("Model ID", style="green")
    table.add_column("Alias", style="yellow")
    table.add_column("Context", style="blue", justify="right")
    table.add_column("Characteristics", style="dim")

    # Group models by provider
    providers = ["anthropic", "openai", "google", "xai"]
    
    for provider in providers:
        models = get_models_by_provider(provider)
        
        # Add provider header row
        if models:
            table.add_row(
                f"[bold]{provider.title()}[/bold]",
                "",
                "",
                "",
                "",
                style="bold cyan"
            )
            
            # Add each model
            for config in models:
                characteristics = []
                characteristics.append(config.characteristics.conversation_style)
                characteristics.append(f"~{config.characteristics.avg_response_length}")
                
                table.add_row(
                    "",  # Empty provider column for individual models
                    config.model_id,
                    config.aliases[0] if config.aliases else "-",
                    f"{config.context_window // 1000}k",
                    ", ".join(characteristics) if characteristics else "-"
                )
            
            # Add spacing between providers
            if provider != providers[-1]:
                table.add_row("", "", "", "", "")

    console.print(table)
    
    # Add usage hints
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("  pidgin chat -a claude -b gpt")
    console.print("  pidgin chat -a opus -b gemini-1.5-pro")
    console.print("  pidgin chat -a gpt-4.1 -b claude-haiku")
    
    console.print("\n[#4c566a]Use either the model ID or alias with the -a and -b flags.[/#4c566a]")


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--example", help="Show example for specific dimension combination")
@click.option("--list", "list_only", is_flag=True, help="List just dimension names")
@click.option("--detailed", is_flag=True, help="Show detailed info about a dimension")
@click.argument("dimension", required=False)
def dimensions(example, list_only, detailed, dimension):
    """Explore dimensional prompt system for conversation setup.
    
    Dimensional prompts let you quickly configure conversation dynamics by
    combining different aspects like context (peers/debate/teaching) and
    topics (philosophy/science/language).
    
    [bold]FORMAT:[/bold]
        [#4c566a]-d context:topic[:mode][/#4c566a]
    
    [bold]EXAMPLES:[/bold]
    
    List all dimensions:
        [#4c566a]pidgin dimensions[/#4c566a]
    
    Show specific dimension:
        [#4c566a]pidgin dimensions context --detailed[/#4c566a]
    
    See example output:
        [#4c566a]pidgin dimensions --example peers:philosophy[/#4c566a]
    
    [bold]QUICK COMBINATIONS:[/bold]
        • [green]peers:philosophy[/green] → Collaborative philosophical discussion
        • [green]debate:science:analytical[/green] → Analytical scientific debate
        • [green]teaching:language[/green] → Teaching session about language
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
    console.print("  [#4c566a]pidgin chat -d context:topic[:mode][/#4c566a]\n")

    all_dims = generator.get_all_dimensions()

    for dim_name, dim in all_dims.items():
        console.print(f"[bold cyan]{dim_name.upper()}[/bold cyan] - {dim.description}")
        console.print(f"  Required: {'Yes' if dim.required else 'No'}")
        console.print("  Values:")

        for value, desc in dim.values.items():
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
        ("teaching:language", "Teaching session about language"),
        ("interview:meta:exploratory", "Exploratory interview about the conversation itself"),
    ]

    for example_spec, description in examples:
        console.print(f"  [#4c566a]pidgin chat -d {example_spec}[/#4c566a]")
        console.print(f"    → {description}")
    console.print()


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-a", "--model-a", required=True,
    help="First model (e.g., 'claude', 'gpt-4', 'opus')"
)
@click.option(
    "-b", "--model-b", required=True,
    help="Second model (e.g., 'gpt', 'gemini', 'haiku')"
)
@click.option(
    "-t", "--turns", default=10, 
    help="Number of conversation turns (default: 10, recommended: 20-100)"
)
@click.option("-p", "--prompt", 
              help="Initial prompt (string or path to .md file)")
@click.option("-d", "--dimensions", 
              help="Use dimensional prompt system - e.g., 'peers:philosophy' or 'debate:science:analytical'")
@click.option(
    "-s", "--save-to",
    help="Custom path to save conversation (defaults to ./pidgin_output/)"
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help="Path to custom configuration file"
)
@click.option(
    "-m", "--manual",
    is_flag=True,
    help="Manual mode - pause after each turn"
)
@click.option(
    "--convergence-threshold",
    type=click.FloatRange(0.0, 1.0),
    help="Stop when convergence reaches this threshold (0.0-1.0)"
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(),
    help="Override default output directory"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Show detailed event information"
)
@click.option(
    "-q", "--quiet",
    is_flag=True,
    help="Minimal output - only show essential information"
)
@click.option(
    "--timing",
    is_flag=True,
    help="Show detailed timing information"
)
@click.option(
    "--choose-names",
    is_flag=True,
    help="Let agents choose their own names",
)
@click.option(
    "-w", "--awareness",
    type=click.Choice(['none', 'basic', 'firm', 'research']),
    default='basic',
    help="Awareness level for both agents",
)
@click.option(
    "--awareness-a",
    type=click.Choice(['none', 'basic', 'firm', 'research']),
    help="Awareness level for agent A only",
)
@click.option(
    "--awareness-b",
    type=click.Choice(['none', 'basic', 'firm', 'research']),
    help="Awareness level for agent B only",
)
@click.option(
    "--show-system-prompts",
    is_flag=True,
    help="Display system prompts at start",
)
@click.option(
    "--temperature",
    type=click.FloatRange(0.0, 2.0),
    help="Temperature for both models (0.0-2.0)",
)
@click.option(
    "--temp-a",
    type=click.FloatRange(0.0, 2.0),
    help="Temperature for model A only",
)
@click.option(
    "--temp-b",
    type=click.FloatRange(0.0, 2.0),
    help="Temperature for model B only",
)
def chat(
    model_a,
    model_b,
    turns,
    prompt,
    dimensions,
    save_to,
    config,
    manual,
    convergence_threshold,
    output_dir,
    verbose,
    quiet,
    timing,
    choose_names,
    awareness,
    awareness_a,
    awareness_b,
    show_system_prompts,
    temperature,
    temp_a,
    temp_b,
):
    """Run a conversation between two AI agents.

    This command starts a conversation that will run for the specified number of turns.
    The conversation is saved to ./pidgin_output/ with full event logs and transcripts.

    [bold]EXAMPLES:[/bold]

    [#4c566a]Basic conversation (10 turns):[/#4c566a]
        pidgin chat -a claude -b gpt

    [#4c566a]Longer philosophical discussion:[/#4c566a]
        pidgin chat -a opus -b gpt-4.1 -t 50 -p "What is consciousness?"

    [#4c566a]Using dimensional prompts:[/#4c566a]
        pidgin chat -a claude -b gpt -d peers:philosophy
        pidgin chat -a gpt -b gemini -d debate:language:analytical

    [#4c566a]Let agents name themselves:[/#4c566a]
        pidgin chat -a claude -b gpt --choose-names

    [#4c566a]High convergence monitoring:[/#4c566a]
        pidgin chat -a claude -b gpt -t 100 --convergence-threshold 0.8

    [#4c566a]Different awareness levels:[/#4c566a]
        pidgin chat -a claude -b gpt --awareness research
        pidgin chat -a claude -b gpt --awareness-a firm --awareness-b none
    """
    # Import here to avoid circular imports
    from .core.conductor import Conductor
    from .core.event_bus import EventBus
    from .io.output_manager import OutputManager
    from .config.system_prompts import get_system_prompts, get_awareness_info
    
    # Validate exclusive options
    if quiet and verbose:
        raise click.BadParameter("Cannot use both --quiet and --verbose")
    
    # Build initial prompt
    initial_prompt = _build_initial_prompt(
        custom_prompt=prompt,
        dimensions=dimensions,
    )
    
    # Get model configurations
    try:
        config_a = get_model_config(model_a)
        config_b = get_model_config(model_b)
        model_a_id = config_a.model_id if config_a else model_a
        model_b_id = config_b.model_id if config_b else model_b
    except ValueError as e:
        console.print(f"[red]Model error: {e}[/red]")
        console.print("\n[#4c566a]Run 'pidgin models' to see available models.[/#4c566a]")
        raise click.Abort()
    
    # Determine temperatures for each model
    if temperature is not None:
        # --temperature sets both
        temperature_a = temperature_b = temperature
    else:
        # Use individual settings or None
        temperature_a = temp_a
        temperature_b = temp_b
    
    # Determine display mode
    if quiet:
        display_mode = "quiet"
    elif verbose:
        display_mode = "verbose"
    else:
        display_mode = "normal"
    
    # Create output manager
    output_manager = OutputManager(output_dir)  # Uses output_dir if provided
    
    # Get provider objects
    providers_map = {}
    try:
        # Agent A
        provider_a = get_provider_for_model(model_a)
        if hasattr(provider_a, "model"):
            providers_map[provider_a.model] = provider_a
        else:
            providers_map[model_a_id] = provider_a
            
        # Agent B  
        provider_b = get_provider_for_model(model_b)
        if hasattr(provider_b, "model"):
            providers_map[provider_b.model] = provider_b
        else:
            providers_map[model_b_id] = provider_b
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
    
    # Create event-driven CONDUCTOR with output manager
    conductor = Conductor(providers_map, output_manager, console)
    
    # Create agents with temperature settings
    agent_a_obj = Agent(id="agent_a", model=model_a_id, temperature=temperature_a)
    agent_b_obj = Agent(id="agent_b", model=model_b_id, temperature=temperature_b)
    
    # Show system prompts if requested
    if show_system_prompts:
        from .config.system_prompts import get_system_prompts, get_awareness_info
        
        # Determine actual awareness levels
        actual_awareness_a = awareness_a if awareness_a else awareness
        actual_awareness_b = awareness_b if awareness_b else awareness
        
        system_prompts = get_system_prompts(
            awareness_a=actual_awareness_a,
            awareness_b=actual_awareness_b,
            choose_names=choose_names,
            model_a_name=model_a_id,
            model_b_name=model_b_id
        )
        
        console.print(f"\n[bold cyan]System Prompts:[/bold cyan]")
        console.print(f"Agent A Awareness: {actual_awareness_a}")
        console.print(f"Agent B Awareness: {actual_awareness_b}\n")
        
        if system_prompts["agent_a"]:
            console.print(Panel(
                system_prompts["agent_a"],
                title="System Prompt - Agent A",
                border_style="green"
            ))
        else:
            console.print("[#4c566a]Agent A: No system prompt (chaos mode)[/#4c566a]")
            
        if system_prompts["agent_b"]:
            console.print(Panel(
                system_prompts["agent_b"],
                title="System Prompt - Agent B", 
                border_style="blue"
            ))
        else:
            console.print("[#4c566a]Agent B: No system prompt (chaos mode)[/#4c566a]")
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
                awareness_a=awareness_a if awareness_a else awareness,
                awareness_b=awareness_b if awareness_b else awareness,
                temperature_a=temperature_a,
                temperature_b=temperature_b,
            )
        )

        # Show completion summary
        if not quiet:
            console.print(f"\n[bold green]Conversation completed![/bold green]")
            console.print(f"Total messages: [cyan]{len(conversation.messages)}[/cyan]")
            console.print(f"Conversation ID: {conversation.id}")

            # Save transcript
            if conductor.current_conv_dir:
                transcript_path = (
                    conductor.current_conv_dir / "conversation.md"
                )
                if transcript_path.exists():
                    console.print(
                        f"\n[#4c566a]Transcript saved to: {transcript_path}[/#4c566a]"
                    )

    except KeyboardInterrupt:
        console.print("\n[yellow]Conversation interrupted by user.[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-n", "--count", 
    default=10,
    help="Number of conversations to run (default: 10)"
)
@click.option(
    "-a", "--model-a", 
    required=True,
    help="First model (e.g., 'claude', 'gpt-4', 'opus')"
)
@click.option(
    "-b", "--model-b",
    required=True,
    help="Second model (e.g., 'gpt', 'gemini', 'haiku')"
)
@click.option(
    "-t", "--turns",
    default=20,
    help="Number of turns per conversation (default: 20)"
)
@click.option(
    "-p", "--prompt",
    help="Initial prompt for all conversations"
)
@click.option(
    "-d", "--dimensions",
    help="Dimensional prompt (e.g., 'peers:philosophy')"
)
@click.option(
    "--parallel",
    default=1,
    help="Number of conversations to run in parallel (default: 1)"
)
@click.option(
    "--name",
    help="Experiment name (for output organization)"
)
@click.option(
    "--temperature",
    type=click.FloatRange(0.0, 2.0),
    help="Temperature for both models"
)
@click.option(
    "--convergence-threshold",
    type=click.FloatRange(0.0, 1.0),
    help="Stop conversations at this convergence level"
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(),
    help="Override default output directory"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Show detailed progress"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be run without executing"
)
def experiment(
    count,
    model_a,
    model_b,
    turns,
    prompt,
    dimensions,
    parallel,
    name,
    temperature,
    convergence_threshold,
    output_dir,
    verbose,
    dry_run,
):
    """Run batch experiments with multiple conversations.
    
    This command runs multiple identical conversations to gather statistical
    data about convergence patterns, conversation dynamics, and emergent behaviors.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Basic experiment (10 conversations):[/#4c566a]
        pidgin experiment -a claude -b gpt -n 10
    
    [#4c566a]Convergence threshold testing:[/#4c566a]
        pidgin experiment -a claude -b gpt -n 100 -t 50 --convergence-threshold 0.85
    
    [#4c566a]Temperature comparison:[/#4c566a]
        pidgin experiment -a claude -b gpt -n 50 --temperature 0.3 --name "low-temp"
        pidgin experiment -a claude -b gpt -n 50 --temperature 0.9 --name "high-temp"
    
    [#4c566a]Model comparison study:[/#4c566a]
        pidgin experiment -a claude -b claude -n 100 --name "claude-self"
        pidgin experiment -a gpt -b gpt -n 100 --name "gpt-self"
        pidgin experiment -a claude -b gpt -n 100 --name "claude-gpt"
    
    [bold]OUTPUT:[/bold]
    
    Results are saved to:
        ./pidgin_output/experiments/<date>/<name>/
    
    Including:
        • Individual conversation logs
        • Aggregate statistics (summary.json)
        • Convergence analysis
        • Pattern detection results
    """
    import json
    from datetime import datetime
    from pathlib import Path
    import asyncio
    from .core.conductor import Conductor
    from .io.output_manager import OutputManager
    
    # Validate models
    try:
        config_a = get_model_config(model_a)
        config_b = get_model_config(model_b)
        model_a_id = config_a.model_id if config_a else model_a
        model_b_id = config_b.model_id if config_b else model_b
    except ValueError as e:
        console.print(f"[#bf616a]Model error: {e}[/#bf616a]")
        console.print("\n[#4c566a]Run 'pidgin models' to see available models.[/#4c566a]")
        raise click.Abort()
    
    # Build initial prompt
    initial_prompt = _build_initial_prompt(
        custom_prompt=prompt,
        dimensions=dimensions,
    )
    
    # Create experiment name if not provided
    if not name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{model_a}_{model_b}_{timestamp}"
    
    # Setup experiment directory
    base_output = Path(output_dir) if output_dir else Path("./pidgin_output")
    experiment_dir = base_output / "experiments" / datetime.now().strftime("%Y-%m-%d") / name
    
    if dry_run:
        console.print("\n[bold cyan]◆ Experiment Configuration (DRY RUN)[/bold cyan]")
        console.print(f"  Models: {model_a_id} ↔ {model_b_id}")
        console.print(f"  Conversations: {count}")
        console.print(f"  Turns per conversation: {turns}")
        console.print(f"  Initial prompt: {initial_prompt[:50]}...")
        if temperature is not None:
            console.print(f"  Temperature: {temperature}")
        if convergence_threshold is not None:
            console.print(f"  Convergence threshold: {convergence_threshold}")
        console.print(f"  Parallel execution: {parallel}")
        console.print(f"  Output directory: {experiment_dir}")
        console.print("\n[#4c566a]No conversations will be run (dry run mode)[/#4c566a]")
        return
    
    # Create experiment directory
    experiment_dir.mkdir(parents=True, exist_ok=True)
    
    # Save experiment configuration
    config_data = {
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "model_a": model_a_id,
        "model_b": model_b_id,
        "count": count,
        "turns": turns,
        "initial_prompt": initial_prompt,
        "temperature": temperature,
        "convergence_threshold": convergence_threshold,
        "parallel": parallel,
    }
    
    with open(experiment_dir / "config.json", "w") as f:
        json.dump(config_data, f, indent=2)
    
    console.print(f"\n[bold cyan]◆ Starting Experiment: {name}[/bold cyan]")
    console.print(f"  Output: {experiment_dir}")
    
    # For now, implement sequential execution
    # TODO: Add parallel execution support
    results = []
    convergence_scores = []
    total_turns = []
    
    async def run_single_conversation(index):
        """Run a single conversation in the experiment."""
        # Create conversation-specific output directory
        conv_dir = experiment_dir / f"conversation_{index:03d}"
        conv_dir.mkdir(exist_ok=True)
        
        # Create output manager for this conversation
        output_manager = OutputManager(str(conv_dir.parent))
        output_manager.conversation_dir = conv_dir
        
        # Get providers
        try:
            provider_a = get_provider_for_model(model_a)
            provider_b = get_provider_for_model(model_b)
            
            providers_map = {}
            if hasattr(provider_a, "model"):
                providers_map[provider_a.model] = provider_a
            else:
                providers_map[model_a_id] = provider_a
                
            if hasattr(provider_b, "model"):
                providers_map[provider_b.model] = provider_b
            else:
                providers_map[model_b_id] = provider_b
                
        except ValueError as e:
            console.print(f"[#bf616a]Error creating providers: {e}[/#bf616a]")
            return None
        
        # Create conductor
        conductor = Conductor(providers_map, output_manager, console)
        
        # Create agents
        agent_a_obj = Agent(id="agent_a", model=model_a_id, temperature=temperature)
        agent_b_obj = Agent(id="agent_b", model=model_b_id, temperature=temperature)
        
        try:
            # Run conversation with minimal output
            conversation = await conductor.run_conversation(
                agent_a=agent_a_obj,
                agent_b=agent_b_obj,
                initial_prompt=initial_prompt,
                max_turns=turns,
                display_mode="quiet",  # Quiet mode for batch
                show_timing=False,
                choose_names=False,
                awareness_a="basic",
                awareness_b="basic",
                temperature_a=temperature,
                temperature_b=temperature,
                convergence_threshold=convergence_threshold,
            )
            
            # Extract metrics
            # TODO: Get actual convergence scores from conductor
            result = {
                "index": index,
                "id": conversation.id,
                "turns": len(conversation.messages) // 2,
                "completed": True,
                "directory": str(conv_dir),
            }
            
            return result
            
        except Exception as e:
            console.print(f"[#bf616a]Error in conversation {index}: {e}[/#bf616a]")
            return {
                "index": index,
                "completed": False,
                "error": str(e),
            }
    
    # Progress tracking
    with console.status(f"[bold cyan]Running {count} conversations...[/bold cyan]") as status:
        for i in range(count):
            if verbose:
                console.print(f"\n[#4c566a]→ Starting conversation {i+1}/{count}[/#4c566a]")
            else:
                status.update(f"[bold cyan]Running conversation {i+1}/{count}...[/bold cyan]")
            
            result = asyncio.run(run_single_conversation(i))
            if result:
                results.append(result)
                if result["completed"]:
                    total_turns.append(result["turns"])
    
    # Calculate summary statistics
    successful = sum(1 for r in results if r["completed"])
    failed = len(results) - successful
    
    summary = {
        "experiment": config_data,
        "results": {
            "total": count,
            "successful": successful,
            "failed": failed,
            "average_turns": sum(total_turns) / len(total_turns) if total_turns else 0,
            "min_turns": min(total_turns) if total_turns else 0,
            "max_turns": max(total_turns) if total_turns else 0,
        },
        "conversations": results,
    }
    
    # Save summary
    with open(experiment_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    # Display results
    console.print(f"\n[bold green]✓ Experiment Complete[/bold green]")
    console.print(f"  Successful: {successful}/{count}")
    if failed > 0:
        console.print(f"  Failed: {failed}")
    console.print(f"  Average turns: {summary['results']['average_turns']:.1f}")
    console.print(f"  Results saved to: {experiment_dir}")
    
    # TODO: Add more sophisticated analysis
    console.print("\n[#4c566a]Note: Full statistical analysis coming soon![/#4c566a]")


@cli.group()
def experiment():
    """Run and manage batch experiments.
    
    This command group allows you to start, monitor, and manage experiments
    that run multiple conversations for statistical analysis.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Start an experiment in background:[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 20
    
    [#4c566a]Check status of all experiments:[/#4c566a]
        pidgin experiment status
    
    [#4c566a]View logs of running experiment:[/#4c566a]
        pidgin experiment logs exp_abc123
    
    [#4c566a]Stop a running experiment:[/#4c566a]
        pidgin experiment stop exp_abc123
    """
    pass


@experiment.command()
@click.option("-a", "--agent-a", "model_a", required=True, help="First model")
@click.option("-b", "--agent-b", "model_b", required=True, help="Second model")
@click.option("-r", "--repetitions", default=10, help="Number of conversations to run")
@click.option("-t", "--max-turns", default=50, help="Maximum turns per conversation")
@click.option("-p", "--initial-prompt", default="Hello! Let's have a conversation.", help="Initial prompt")
@click.option("--name", help="Experiment name (auto-generated if not provided)")
@click.option("--temperature", type=float, help="Temperature for both models")
@click.option("--convergence-threshold", type=float, help="Stop at convergence threshold")
@click.option("--choose-names", is_flag=True, help="Allow agents to choose names")
@click.option("--max-parallel", type=int, help="Max parallel conversations (auto if not set)")
@click.option("--background/--foreground", default=True, help="Run as daemon (default) or foreground")
def start(model_a, model_b, repetitions, max_turns, initial_prompt, name,
          temperature, convergence_threshold, choose_names, max_parallel, background):
    """Start a new experiment.
    
    By default, experiments run in the background as daemons. Use --foreground
    to run interactively (useful for debugging).
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Basic experiment (background):[/#4c566a]
        pidgin experiment start -a claude -b gpt
    
    [#4c566a]Large experiment with custom parallelism:[/#4c566a]
        pidgin experiment start -a opus -b gpt-4 -r 100 --max-parallel 8
    
    [#4c566a]Run in foreground for debugging:[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 5 --foreground
    """
    import time
    from .experiments import ExperimentConfig, ExperimentManager, ExperimentStore
    from .experiments.parallel_runner import ParallelExperimentRunner
    
    # Generate experiment name if not provided
    if not name:
        name = f"{model_a}_vs_{model_b}_{int(time.time())}"
    
    # Create configuration
    config = ExperimentConfig(
        name=name,
        agent_a_model=model_a,
        agent_b_model=model_b,
        initial_prompt=initial_prompt,
        max_turns=max_turns,
        repetitions=repetitions,
        temperature_a=temperature,
        temperature_b=temperature,
        convergence_threshold=convergence_threshold,
        choose_names=choose_names,
        max_parallel=max_parallel
    )
    
    # Validate configuration
    errors = config.validate()
    if errors:
        console.print(f"[#bf616a]Configuration errors:[/#bf616a]")
        for error in errors:
            console.print(f"  • {error}")
        return
    
    if background:
        # Start as daemon
        manager = ExperimentManager()
        console.print(f"[#8fbcbb]◆ Starting experiment: {config.name}[/#8fbcbb]")
        console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        
        try:
            exp_id = manager.start_experiment(config)
            console.print(f"\n[#a3be8c]✓ Experiment started in background[/#a3be8c]")
            console.print(f"[#4c566a]  ID: {exp_id}[/#4c566a]")
            console.print(f"\n[#4c566a]Check status:[/#4c566a] pidgin experiment status")
            console.print(f"[#4c566a]View logs:[/#4c566a] pidgin experiment logs {exp_id}")
            console.print(f"[#4c566a]Stop:[/#4c566a] pidgin experiment stop {exp_id}")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Failed to start experiment: {str(e)}[/#bf616a]")
            raise
    else:
        # Run in foreground
        storage = ExperimentStore()
        runner = ParallelExperimentRunner(storage)
        
        console.print(f"\n[#8fbcbb]◆ Starting experiment (foreground): {config.name}[/#8fbcbb]")
        console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        if max_parallel:
            console.print(f"[#4c566a]  Parallelism: {max_parallel}[/#4c566a]")
        console.print()
        
        try:
            start_time = time.time()
            experiment_id = asyncio.run(runner.run_experiment(config))
            duration = time.time() - start_time
            
            # Get final status
            status = storage.get_experiment_status(experiment_id)
            
            # Show results
            console.print(f"\n[#a3be8c]✓ Experiment complete![/#a3be8c]")
            console.print(f"[#4c566a]  ID: {experiment_id}[/#4c566a]")
            console.print(f"[#4c566a]  Duration: {duration:.1f}s[/#4c566a]")
            console.print(f"[#4c566a]  Completed: {status.get('completed_conversations', 0)}/{repetitions}[/#4c566a]")
            if status.get('avg_convergence'):
                console.print(f"[#4c566a]  Avg convergence: {status['avg_convergence']:.3f}[/#4c566a]")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Experiment failed: {str(e)}[/#bf616a]")
            raise


@experiment.command()
def status():
    """Show status of all experiments.
    
    Lists recent experiments with their current status, progress, and
    whether they're currently running.
    """
    from .experiments import ExperimentManager
    from rich.table import Table
    
    manager = ExperimentManager()
    experiments = manager.list_experiments(limit=20)
    
    if not experiments:
        console.print("[#4c566a]No experiments found.[/#4c566a]")
        return
    
    # Create table
    table = Table(title="Experiments", title_style="#8fbcbb")
    table.add_column("ID", style="#88c0d0", width=12)
    table.add_column("Name", style="#a3be8c", max_width=30)
    table.add_column("Models", style="#d8dee9")
    table.add_column("Status", style="#ebcb8b")
    table.add_column("Progress", justify="right", style="#d8dee9")
    table.add_column("Running", style="#bf616a", justify="center")
    
    for exp in experiments:
        # Format progress
        total = exp.get('total_conversations', 0)
        completed = exp.get('completed_conversations', 0)
        failed = exp.get('failed_conversations', 0)
        
        if failed > 0:
            progress = f"{completed}/{total} ({failed} failed)"
        else:
            progress = f"{completed}/{total}"
        
        # Format models
        models = f"{exp.get('agent_a_model', '?')} vs {exp.get('agent_b_model', '?')}"
        
        # Running indicator
        running = "●" if exp.get('is_running') else "○"
        
        # Add row
        table.add_row(
            exp['experiment_id'],
            exp['name'],
            models,
            exp['status'],
            progress,
            running
        )
    
    console.print(table)
    console.print(f"\n[#4c566a]● = running, ○ = stopped[/#4c566a]")


@experiment.command()
@click.argument('experiment_id')
def stop(experiment_id):
    """Stop a running experiment gracefully."""
    from .experiments import ExperimentManager
    
    manager = ExperimentManager()
    
    console.print(f"[#ebcb8b]→ Stopping experiment {experiment_id}...[/#ebcb8b]")
    
    if manager.stop_experiment(experiment_id):
        console.print(f"[#a3be8c]✓ Stopped experiment {experiment_id}[/#a3be8c]")
    else:
        console.print(f"[#bf616a]✗ Failed to stop experiment {experiment_id}[/#bf616a]")
        console.print(f"[#4c566a]  (It may not be running)[/#4c566a]")


@experiment.command()
@click.argument('experiment_id')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (like tail -f)')
def logs(experiment_id, lines, follow):
    """Show logs from an experiment.
    
    By default shows the last 50 lines. Use -f to follow the log
    in real-time (press Ctrl+C to stop).
    """
    from .experiments import ExperimentManager
    
    manager = ExperimentManager()
    
    if follow:
        console.print(f"[#4c566a]Following logs for {experiment_id} (Ctrl+C to stop)...[/#4c566a]\n")
        try:
            manager.tail_logs(experiment_id, follow=True)
        except KeyboardInterrupt:
            console.print("\n[#4c566a]Stopped following logs.[/#4c566a]")
    else:
        log_lines = manager.get_logs(experiment_id, lines)
        
        if not log_lines:
            console.print(f"[#bf616a]No logs found for experiment {experiment_id}[/#bf616a]")
            return
        
        # Print logs
        for line in log_lines:
            console.print(line.rstrip(), markup=False)


if __name__ == "__main__":
    cli()