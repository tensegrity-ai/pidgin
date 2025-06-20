import os
# Force color output for rich-click
os.environ['FORCE_COLOR'] = '1'
os.environ['CLICOLOR_FORCE'] = '1'

# Store the original working directory before any imports that might change it
# When running with python -m, the working directory may be changed
ORIGINAL_CWD = os.environ.get('PWD', os.getcwd())

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
        return "Hello! I'm looking forward to your conversation."
    
    # Combine parts
    return " ".join(parts) if all(isinstance(p, str) for p in parts) else "".join(str(p) for p in parts)


def get_provider_for_model(model: str):
    """Determine which provider to use based on the model name"""
    # Check if it's a local model
    if model.startswith("local:"):
        from .providers.local import LocalProvider
        model_name = model.split(":", 1)[1] if ":" in model else "test"
        return LocalProvider(model_name)
    
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
        elif config.provider == "local":
            from .providers.local import LocalProvider
            return LocalProvider(config.model_id.split(":", 1)[1] if ":" in config.model_id else "test")

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
    
    # Setup experiment directory using the original working directory
    if output_dir:
        base_output = Path(output_dir)
    else:
        # Use the original working directory for relative paths
        base_output = Path(ORIGINAL_CWD) / "pidgin_output"
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
    """Run and manage experiment sessions.
    
    Experiments run multiple conversations for statistical analysis.
    Uses a screen-like session model: start experiments with dashboard
    attached, detach to run in background, and resume to reattach.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Start experiment with dashboard:[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 20 --name "test"
    
    [#4c566a]Resume/reattach to experiment:[/#4c566a]
        pidgin experiment resume test
    
    [#4c566a]List experiment sessions:[/#4c566a]
        pidgin experiment list
    
    [#4c566a]Start in background (daemon):[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 100 --name "bg" --daemon
    """
    pass


@experiment.command()
@click.option("-a", "--agent-a", "model_a", required=True, help="First model")
@click.option("-b", "--agent-b", "model_b", required=True, help="Second model")
@click.option("-r", "--repetitions", default=10, help="Number of conversations to run")
@click.option("-t", "--max-turns", default=50, help="Maximum turns per conversation")
@click.option("-p", "--prompt", help="Custom prompt for conversations")
@click.option("-d", "--dimensions", help="Dimensional prompt (e.g., peers:philosophy)")
@click.option("--name", required=True, help="Experiment session name")
@click.option("--temperature", type=click.FloatRange(0.0, 2.0), help="Temperature for both models")
@click.option("--temp-a", type=click.FloatRange(0.0, 2.0), help="Temperature for model A only")
@click.option("--temp-b", type=click.FloatRange(0.0, 2.0), help="Temperature for model B only")
@click.option("--awareness", type=click.Choice(['none', 'basic', 'firm', 'research']), default='basic', help="Awareness level for both agents")
@click.option("--awareness-a", type=click.Choice(['none', 'basic', 'firm', 'research']), help="Awareness level for agent A only")
@click.option("--awareness-b", type=click.Choice(['none', 'basic', 'firm', 'research']), help="Awareness level for agent B only")
@click.option("--convergence-threshold", type=click.FloatRange(0.0, 1.0), help="Stop at convergence threshold")
@click.option("--choose-names", is_flag=True, help="Allow agents to choose names")
@click.option("--max-parallel", type=int, help="Max parallel conversations (auto if not set)")
@click.option("--daemon", is_flag=True, help="Start in background without dashboard")
@click.option("--debug", is_flag=True, help="Run in debug mode (no daemonization)")
def start(model_a, model_b, repetitions, max_turns, prompt, dimensions, name,
          temperature, temp_a, temp_b, awareness, awareness_a, awareness_b,
          convergence_threshold, choose_names, max_parallel, daemon, debug):
    """Start a new experiment session.
    
    By default, starts experiment with dashboard attached (like GNU screen).
    Use --daemon to run in background without dashboard.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Start with dashboard:[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 20 --name "test"
    
    [#4c566a]Start in background (daemon mode):[/#4c566a]
        pidgin experiment start -a opus -b gpt-4 -r 100 --name "prod" --daemon
    
    [#4c566a]Large experiment with custom parallelism:[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 50 --name "parallel" --max-parallel 8
    """
    import time
    from .experiments import ExperimentConfig, ExperimentManager, ExperimentStore
    from .experiments.parallel_runner import ParallelExperimentRunner
    
    # Check if experiment already exists
    storage = ExperimentStore()
    existing = storage.get_experiment_by_name(name)
    if existing:
        console.print(f"[#bf616a]Experiment session '{name}' already exists[/#bf616a]")
        console.print(f"Use 'pidgin experiment resume {name}' to reattach")
        return
    
    # Resolve model aliases to IDs
    from .config.models import resolve_model_id
    model_a_id, config_a = resolve_model_id(model_a)
    model_b_id, config_b = resolve_model_id(model_b)
    
    # Create configuration with resolved IDs
    config = ExperimentConfig(
        name=name,
        agent_a_model=model_a_id,  # Use resolved ID
        agent_b_model=model_b_id,  # Use resolved ID
        custom_prompt=prompt,
        dimensions=dimensions,
        max_turns=max_turns,
        repetitions=repetitions,
        temperature=temperature,
        temperature_a=temp_a,
        temperature_b=temp_b,
        awareness=awareness,
        awareness_a=awareness_a,
        awareness_b=awareness_b,
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
    
    if debug:
        # Debug mode - run directly without daemonization
        console.print(f"[#ebcb8b]◆ Starting experiment '{name}' in DEBUG mode[/#ebcb8b]")
        console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        console.print(f"\n[#bf616a]Running in foreground - press Ctrl+C to stop[/#bf616a]\n")
        
        # Run directly without daemon
        from .experiments import ExperimentStore
        from .experiments.parallel_runner import ParallelExperimentRunner
        
        storage = ExperimentStore()
        runner = ParallelExperimentRunner(storage)
        
        try:
            # Create experiment and run it
            exp_id = asyncio.run(runner.run_experiment(config))
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' completed[/#a3be8c]")
        except KeyboardInterrupt:
            console.print(f"\n[#ebcb8b]Experiment interrupted by user[/#ebcb8b]")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Experiment failed: {e}[/#bf616a]")
            import traceback
            traceback.print_exc()
        return
        
    if daemon:
        # Start as daemon (headless mode)
        base_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
        manager = ExperimentManager(base_dir=base_dir)
        console.print(f"[#8fbcbb]◆ Starting experiment '{name}' in background[/#8fbcbb]")
        console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        
        try:
            # Use the original working directory captured at module import
            exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' started in background[/#a3be8c]")
            console.print(f"[#4c566a]Use 'pidgin experiment resume {name}' to attach dashboard[/#4c566a]")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Failed to start experiment: {str(e)}[/#bf616a]")
            raise
    else:
        # Interactive mode - start with dashboard attached
        from .dashboard import ExperimentDashboard
        
        # Start experiment daemon in background
        base_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
        manager = ExperimentManager(base_dir=base_dir)
        
        try:
            # Start experiment (launches daemon in background)
            exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
            
            # Wait a moment for daemon to initialize and create database
            import time
            time.sleep(2)
            
            # Get database path for the experiment
            db_path = base_dir / "experiments.db"
            
            # Create and run dashboard
            console.print(f"\n[#8fbcbb]◆ Starting experiment '{name}' with dashboard[/#8fbcbb]")
            console.print(f"[#4c566a]Press 'D' to detach, Ctrl+C to pause[/#4c566a]\n")
            
            dashboard = ExperimentDashboard(db_path, experiment_name=name)
            asyncio.run(dashboard.run())
            
        except KeyboardInterrupt:
            console.print("\n[#ebcb8b]Experiment paused by user[/#ebcb8b]")
            console.print(f"Use 'pidgin experiment resume {name}' to continue")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Failed to start experiment: {str(e)}[/#bf616a]")
            raise


@experiment.command()
@click.argument('name')
def resume(name):
    """Reattach to an experiment session (paused or detached).
    
    Works for both paused experiments and running experiments that have
    been detached from the dashboard. This is the universal command to
    "show me this experiment".
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Resume paused experiment:[/#4c566a]
        pidgin experiment resume mytest
    
    [#4c566a]Reattach to detached experiment:[/#4c566a]
        pidgin experiment resume background_run
    """
    from .experiments import ExperimentStore, ExperimentManager
    
    base_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
    storage = ExperimentStore()
    manager = ExperimentManager(base_dir=base_dir)
    
    # Find experiment by name
    experiment = storage.get_experiment_by_name(name)
    if not experiment:
        console.print(f"[#bf616a]Experiment session '{name}' not found[/#bf616a]")
        console.print("\nAvailable sessions:")
        # List available experiments
        experiments = storage.list_experiments(limit=10)
        if experiments:
            from rich.table import Table
            table = Table(show_header=False)
            table.add_column("Name", style="#88c0d0")
            table.add_column("Status", style="#ebcb8b")
            table.add_column("Progress", style="#d8dee9")
            table.add_column("Models", style="#4c566a")
            for exp in experiments:
                total = exp.get('total_conversations', 0)
                completed = exp.get('completed_conversations', 0)
                table.add_row(
                    exp['name'],
                    exp['status'],
                    f"{completed}/{total}",
                    f"{exp.get('agent_a_model', '?')} ↔ {exp.get('agent_b_model', '?')}"
                )
            console.print(table)
        else:
            console.print("[#4c566a]No experiments found[/#4c566a]")
        return
    
    # Check experiment status
    if experiment['status'] == 'completed':
        console.print(f"[#ebcb8b]Experiment '{name}' is completed[/#ebcb8b]")
        console.print(f"Use 'pidgin experiment results {name}' to view results")
        return
    elif experiment['status'] == 'failed':
        console.print(f"[#bf616a]Experiment '{name}' failed[/#bf616a]")
        return
    
    # Get database path
    db_path = base_dir / "experiments.db"
    if not db_path.exists():
        console.print(f"[#bf616a]Database not found[/#bf616a]")
        return
    
    # Create dashboard for this specific experiment
    dashboard = ExperimentDashboard(db_path, experiment_name=name)
    
    if experiment['status'] == 'paused':
        console.print(f"[#8fbcbb]◆ Resuming paused experiment '{name}'...[/#8fbcbb]")
        # TODO: Actually resume the experiment runner
        # For now, just attach the dashboard
    else:
        console.print(f"[#8fbcbb]◆ Reattaching to experiment '{name}'...[/#8fbcbb]")
    
    console.print(f"[#4c566a]Press [D] to detach, [S] to stop experiment[/#4c566a]\n")
    
    try:
        from .experiments.dashboard import run_dashboard
        result = asyncio.run(run_dashboard(experiment['experiment_id']))
        
        if result['detached']:
            console.print(f"\n[#4c566a]Detached from experiment '{name}'[/#4c566a]")
            console.print(f"[#4c566a]Use 'pidgin experiment resume {name}' to reattach[/#4c566a]")
        elif result['stopped']:
            console.print(f"\n[#bf616a]Experiment '{name}' stopped[/#bf616a]")
    except KeyboardInterrupt:
        console.print(f"\n[#4c566a]Dashboard interrupted[/#4c566a]")


@experiment.command()
@click.argument('experiment_name_or_id')
def dashboard(experiment_name_or_id):
    """Open live dashboard for an experiment.
    
    Shows real-time metrics and progress for a running experiment.
    Press 'Q' to quit the dashboard.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Monitor by name:[/#4c566a]
        pidgin experiment dashboard mytest
    
    [#4c566a]Monitor by ID:[/#4c566a]
        pidgin experiment dashboard exp_a1b2c3d4
    """
    from .experiments.storage import ExperimentStore
    from .experiments.dashboard import run_dashboard
    import asyncio
    
    storage = ExperimentStore()
    
    # Try to find by name first, then by ID
    experiment = storage.get_experiment_by_name(experiment_name_or_id)
    if not experiment:
        # Try as ID
        experiment = storage.get_experiment(experiment_name_or_id)
    
    if not experiment:
        console.print(f"[#bf616a]Experiment '{experiment_name_or_id}' not found[/#bf616a]")
        console.print("\n[#4c566a]Use 'pidgin experiment list' to see available experiments[/#4c566a]")
        return
    
    experiment_id = experiment['experiment_id']
    
    console.print(f"[#88c0d0]◆ Opening dashboard for: {experiment['name']}[/#88c0d0]")
    console.print("[#4c566a]Press [D] to detach, [S] to stop experiment[/#4c566a]\n")
    
    try:
        result = asyncio.run(run_dashboard(experiment_id))
        
        if result['detached']:
            console.print(f"\n[#4c566a]Detached from experiment '{experiment['name']}'[/#4c566a]")
            console.print(f"[#4c566a]Use 'pidgin experiment dashboard {experiment['name']}' to reattach[/#4c566a]")
        elif result['stopped']:
            console.print(f"\n[#bf616a]Experiment '{experiment['name']}' stopped[/#bf616a]")
    except KeyboardInterrupt:
        console.print(f"\n[#4c566a]Dashboard interrupted[/#4c566a]")


@experiment.command()
@click.option("--all", is_flag=True, help="Show completed experiments too")
def list(all):
    """List experiment sessions (like screen -list).
    
    Shows active experiment sessions with their status and progress.
    Use --all to include completed experiments.
    """
    from .experiments import ExperimentStore
    from rich.table import Table
    
    storage = ExperimentStore()
    
    experiments = storage.list_experiments(limit=50 if all else 20)
    
    if not experiments:
        console.print("No experiment sessions found")
        return
    
    # Create table
    table = Table(title="Experiment Sessions")
    table.add_column("Name", style="#88c0d0")
    table.add_column("Status", style="#a3be8c")
    table.add_column("Progress", justify="right")
    table.add_column("Models", style="#d8dee9")
    table.add_column("Started", style="#4c566a")
    
    for exp in experiments:
        # Skip completed/failed unless --all
        if not all and exp['status'] in ['completed', 'failed']:
            continue
            
        # Format status with attachment info
        status = exp['status']
        if exp['status'] == 'running' and exp.get('dashboard_attached'):
            status = "running (attached)"
        elif exp['status'] == 'running':
            status = "running (detached)"
            
        # Format progress
        total = exp.get('total_conversations', 0)
        completed = exp.get('completed_conversations', 0)
        progress = f"{completed}/{total}"
        
        # Format models
        models = f"{exp.get('agent_a_model', '?')} ↔ {exp.get('agent_b_model', '?')}"
        
        # Format start time
        from datetime import datetime
        if exp.get('created_at'):
            start_time = datetime.fromisoformat(exp['created_at'])
            started = start_time.strftime("%m/%d %H:%M")
        else:
            started = "unknown"
        
        # Add row
        table.add_row(
            exp['name'],
            status,
            progress,
            models,
            started
        )
    
    console.print(table)


@experiment.command()
def monitor():
    """Monitor rate limits and active conversations.
    
    Real-time debugging dashboard showing:
    - Active conversations with turn counts and last messages
    - Provider rate limit usage (maxed/high/ok)
    - Recent API errors (rate limits, overloaded, token limits)
    - Live status updates every second
    
    Useful for debugging rate limit issues and monitoring experiment health.
    """
    from .dashboard.rate_monitor import RateLimitMonitor
    from pathlib import Path
    
    db_path = Path("./pidgin_output/experiments/experiments.db")
    if not db_path.exists():
        console.print("[#bf616a]No experiments database found[/#bf616a]")
        console.print("[#4c566a]Start an experiment first with 'pidgin experiment start'[/#4c566a]")
        return
        
    console.print("[#8fbcbb]◆ Starting rate limit monitor...[/#8fbcbb]")
    console.print("[#4c566a]Press Ctrl+C to exit[/#4c566a]\n")
    
    monitor = RateLimitMonitor(db_path)
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        console.print("\n[#4c566a]Monitor stopped[/#4c566a]")


@experiment.command()
@click.argument('experiment_id')
def stop(experiment_id):
    """Stop a running experiment gracefully."""
    from .experiments import ExperimentManager
    
    base_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
    manager = ExperimentManager(base_dir=base_dir)
    
    console.print(f"[#ebcb8b]→ Stopping experiment {experiment_id}...[/#ebcb8b]")
    
    if manager.stop_experiment(experiment_id):
        console.print(f"[#a3be8c]✓ Stopped experiment {experiment_id}[/#a3be8c]")
    else:
        console.print(f"[#bf616a]✗ Failed to stop experiment {experiment_id}[/#bf616a]")
        console.print(f"[#4c566a]  (It may not be running)[/#4c566a]")


@experiment.command(name='stop-all')
@click.option('--force', is_flag=True, help='Force kill all experiment processes')
def stop_all(force):
    """KILLSWITCH: Stop ALL running experiments immediately.
    
    This command will:
    - Find all running experiment daemons
    - Gracefully stop them (or force kill with --force)
    - Update database to mark experiments as failed
    - Clean up any orphaned processes
    
    [bold red]WARNING:[/bold red] This will terminate all experiments without saving state!
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Graceful stop of all experiments:[/#4c566a]
        pidgin experiment stop-all
    
    [#4c566a]Force kill all experiments:[/#4c566a]
        pidgin experiment stop-all --force
    """
    import signal
    import subprocess
    from .experiments import ExperimentStore
    
    console.print("[bold red]◆ KILLSWITCH ACTIVATED[/bold red]")
    console.print("[#ebcb8b]→ Finding all running experiments...[/#ebcb8b]")
    
    daemon_pids = []
    
    # First check PID files
    pid_locations = [
        Path("./pidgin_output/experiments"),
        Path(ORIGINAL_CWD) / "pidgin_output/experiments",
        Path.home() / "work/pidgin/pidgin_output/experiments"
    ]
    
    console.print("[#4c566a]  Checking PID files...[/#4c566a]")
    for pid_dir in pid_locations:
        if pid_dir.exists():
            for pid_file in pid_dir.glob("*.pid"):
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                        # Check if process is still running
                        os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
                        daemon_pids.append((pid, pid_file))
                        console.print(f"[#4c566a]  Found PID {pid} from {pid_file.name}[/#4c566a]")
                except (FileNotFoundError, ValueError, ProcessLookupError):
                    # PID file exists but process is gone, clean it up
                    try:
                        pid_file.unlink()
                        console.print(f"[#4c566a]  Cleaned up stale PID file: {pid_file.name}[/#4c566a]")
                    except:
                        pass
    
    # Also check running processes as fallback
    console.print("[#4c566a]  Scanning processes...[/#4c566a]")
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        for line in result.stdout.splitlines():
            if "pidgin.experiments.daemon_launcher" in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = int(parts[1])
                    # Only add if not already found via PID file
                    if not any(p[0] == pid for p in daemon_pids):
                        daemon_pids.append((pid, None))
                        console.print(f"[#4c566a]  Found daemon process: PID {pid}[/#4c566a]")
    
    except subprocess.CalledProcessError as e:
        console.print(f"[#ebcb8b]  Could not scan processes: {e}[/#ebcb8b]")
    
    if not daemon_pids:
        console.print("[#a3be8c]✓ No running experiment daemons found[/#a3be8c]")
    else:
        # Kill the processes
        kill_signal = signal.SIGKILL if force else signal.SIGTERM
        signal_name = "SIGKILL" if force else "SIGTERM"
        
        console.print(f"\n[#ebcb8b]→ Sending {signal_name} to {len(daemon_pids)} processes...[/#ebcb8b]")
        
        for pid, pid_file in daemon_pids:
            try:
                os.kill(pid, kill_signal)
                console.print(f"[#a3be8c]  ✓ Killed PID {pid}[/#a3be8c]")
                # Clean up PID file if we have it
                if pid_file and pid_file.exists():
                    pid_file.unlink()
                    console.print(f"[#a3be8c]  ✓ Removed PID file {pid_file.name}[/#a3be8c]")
            except ProcessLookupError:
                console.print(f"[#4c566a]  - PID {pid} already gone[/#4c566a]")
                # Clean up stale PID file
                if pid_file and pid_file.exists():
                    pid_file.unlink()
            except PermissionError:
                console.print(f"[#bf616a]  ✗ Permission denied for PID {pid}[/#bf616a]")
    
    # Update database for all running experiments
    console.print("\n[#ebcb8b]→ Updating experiment database...[/#ebcb8b]")
    
    # Check multiple possible database locations
    db_locations = [
        Path("./pidgin_output/experiments/experiments.db"),
        Path(ORIGINAL_CWD) / "pidgin_output/experiments/experiments.db",
        Path.home() / "work/pidgin/pidgin_output/experiments/experiments.db"
    ]
    
    updated_count = 0
    for db_path in db_locations:
        if db_path.exists():
            console.print(f"[#4c566a]  Checking {db_path}...[/#4c566a]")
            try:
                storage = ExperimentStore(db_path.parent)
                
                # Get running experiments
                experiments = storage.list_experiments(status_filter='running')
                
                for exp in experiments:
                    storage.update_experiment_status(exp['experiment_id'], 'failed')
                    console.print(f"[#a3be8c]  ✓ Marked '{exp['name']}' as failed[/#a3be8c]")
                    updated_count += 1
                
                # Also update any running conversations
                with storage.get_connection() as conn:
                    cursor = conn.execute(
                        "UPDATE conversations SET status = 'failed' WHERE status = 'running'"
                    )
                    conv_count = cursor.rowcount
                    if conv_count > 0:
                        console.print(f"[#a3be8c]  ✓ Marked {conv_count} conversations as failed[/#a3be8c]")
            except Exception as e:
                console.print(f"[#bf616a]  ✗ Error accessing {db_path}: {e}[/#bf616a]")
    
    if updated_count == 0 and not daemon_pids:
        console.print("\n[#4c566a]No active experiments found in any location[/#4c566a]")
    else:
        console.print(f"\n[bold green]✓ KILLSWITCH COMPLETE[/bold green]")
        console.print(f"[#4c566a]  {len(daemon_pids)} processes killed[/#4c566a]")
        console.print(f"[#4c566a]  {updated_count} experiments marked as failed[/#4c566a]")
        console.print(f"\n[#ebcb8b]All experiments have been forcefully stopped.[/#ebcb8b]")


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
    
    base_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
    manager = ExperimentManager(base_dir=base_dir)
    
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


# Dashboard command removed - now integrated into start/resume workflow


@cli.command(name="check-apis", context_settings={"help_option_names": ["-h", "--help"]})
def check_apis():
    """Check status of all configured API providers.
    
    Tests connectivity and reports any issues with API keys or quotas.
    
    [bold]EXAMPLE:[/bold]
        [#4c566a]pidgin check-apis[/#4c566a]
    
    This will test all configured providers and show:
    • ✓ Connected APIs with available models
    • ✗ APIs with errors (auth, billing, etc.)
    • ⚠ APIs without configured keys
    """
    import asyncio
    import os
    from .providers.anthropic import AnthropicProvider
    from .providers.openai import OpenAIProvider
    from .providers.google import GoogleProvider  
    from .providers.xai import xAIProvider
    from .config.models import MODELS
    
    console.print(Panel.fit(
        "[bold]◆ Checking API Status[/bold]", 
        border_style="#8fbcbb"
    ))
    console.print()
    
    async def check_provider(provider_name: str, model_id: str) -> tuple[str, str, str]:
        """Check a single provider."""
        try:
            # Create provider instance
            if provider_name == "anthropic":
                if not os.getenv("ANTHROPIC_API_KEY"):
                    return provider_name, "warning", "No API key set (ANTHROPIC_API_KEY)"
                provider = AnthropicProvider(model_id)
            elif provider_name == "openai":
                if not os.getenv("OPENAI_API_KEY"):
                    return provider_name, "warning", "No API key set (OPENAI_API_KEY)"
                provider = OpenAIProvider(model_id)
            elif provider_name == "google":
                if not os.getenv("GOOGLE_API_KEY"):
                    return provider_name, "warning", "No API key set (GOOGLE_API_KEY)"
                provider = GoogleProvider(model_id)
            elif provider_name == "xai":
                if not os.getenv("XAI_API_KEY"):
                    return provider_name, "warning", "No API key set (XAI_API_KEY)"
                provider = xAIProvider(model_id)
            else:
                return provider_name, "error", "Unknown provider"
            
            # Test with a simple message
            from pidgin.core.types import Message
            messages = [Message(role="user", content="Say 'test' in one word", agent_id="test")]
            
            response = ""
            async for chunk in provider.stream_response(messages):
                response += chunk
                if len(response) > 10:  # Got enough response
                    break
                    
            return provider_name, "success", f"Connected ({model_id} available)"
            
        except Exception as e:
            error_msg = str(e)
            # Clean up error messages
            if "credit" in error_msg.lower() or "billing" in error_msg.lower():
                return provider_name, "error", "Credit balance low or billing issue"
            elif "invalid" in error_msg.lower() and "key" in error_msg.lower():
                return provider_name, "error", "Invalid API key"
            elif "authentication" in error_msg.lower():
                return provider_name, "error", "Authentication failed"
            else:
                return provider_name, "error", error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
    
    async def check_all():
        """Check all providers."""
        # Get unique providers and a sample model for each
        providers_to_check = {}
        for model_id, config in MODELS.items():
            if config.provider not in providers_to_check:
                providers_to_check[config.provider] = model_id
        
        # Check each provider
        tasks = []
        for provider, model_id in providers_to_check.items():
            tasks.append(check_provider(provider, model_id))
        
        results = await asyncio.gather(*tasks)
        
        # Display results
        table = Table(show_header=True, box=None)
        table.add_column("Provider", style="#8fbcbb", width=15)
        table.add_column("Status", width=10)
        table.add_column("Details", style="#4c566a")
        
        for provider, status, details in sorted(results):
            if status == "success":
                status_icon = "[#a3be8c]✓[/#a3be8c]"
            elif status == "warning":
                status_icon = "[#ebcb8b]⚠[/#ebcb8b]"
            else:
                status_icon = "[#bf616a]✗[/#bf616a]"
            
            table.add_row(
                provider.title(),
                status_icon,
                details
            )
        
        console.print(table)
        console.print()
        
        # Summary
        success_count = sum(1 for _, status, _ in results if status == "success")
        total_count = len(results)
        
        if success_count == total_count:
            console.print(f"[#a3be8c]◆ All {total_count} providers are working correctly![/#a3be8c]")
        elif success_count > 0:
            console.print(f"[#ebcb8b]◆ {success_count}/{total_count} providers are working[/#ebcb8b]")
        else:
            console.print(f"[#bf616a]◆ No providers are currently working[/#bf616a]")
            console.print("\n[#4c566a]Please check your API keys and billing status[/#4c566a]")
    
    # Run the check
    asyncio.run(check_all())


if __name__ == "__main__":
    cli()