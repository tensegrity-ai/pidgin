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
from .core.types import Agent
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


if __name__ == "__main__":
    cli()