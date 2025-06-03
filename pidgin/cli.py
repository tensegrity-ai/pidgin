import click
import asyncio
import os
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel
from pidgin.config import MODEL_SHORTCUTS
from .models import MODELS, get_model_config, get_models_by_provider
from .types import Agent
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .router import DirectRouter
from .dialogue import DialogueEngine
from .transcripts import TranscriptManager
from .checkpoint import ConversationState, CheckpointManager
from .config_manager import Config, load_config
from .dimensional_prompts import DimensionalPromptGenerator

console = Console()


def _build_initial_prompt(custom_prompt: Optional[str], 
                         dimensions: Optional[str],
                         puzzle: Optional[str] = None,
                         experiment: Optional[str] = None,
                         topic_content: Optional[str] = None) -> str:
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
                topic_content=topic_content
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
    
    # Fallback to prefix matching for custom models
    if model.startswith("claude"):
        return AnthropicProvider(model)
    elif model.startswith("gpt") or model.startswith("o3") or model.startswith("o4"):
        return OpenAIProvider(model)
    else:
        raise ValueError(f"Unknown model type: {model}. Model should start with 'claude' or 'gpt'/'o3'/'o4'")


@click.group()
@click.help_option('-h', '--help')
def cli():
    """Pidgin - AI conversation research tool"""
    pass


@cli.command()
@click.help_option('-h', '--help')
@click.option('-a', '--model-a', default='claude', help='First model (default: claude)')
@click.option('-b', '--model-b', default='claude', help='Second model (default: claude)')
@click.option('-t', '--turns', default=10, help='Number of conversation turns (default: 10)')
@click.option('-p', '--prompt', help='Custom initial prompt')
@click.option('-d', '--dimensions', help='Dimensional prompt (e.g., peers:philosophy)')
@click.option('--puzzle', help='Specific puzzle name for puzzles topic')
@click.option('--experiment', help='Specific thought experiment name')
@click.option('--topic-content', help='Custom content for puzzles/experiments')
@click.option('-s', '--save-to', help='Save transcript to specific location')
@click.option('-c', '--config', type=click.Path(exists=True), help='Path to config file')
@click.option('-n', '--no-attractor-detection', '--no-detection', is_flag=True, help='Disable attractor detection')
@click.option('-m', '--manual', '--conductor', is_flag=True, help='Enable manual conductor mode for message-by-message control')
@click.option('-f', '--flowing', is_flag=True, help='Enable flowing conductor mode (auto-flows until Ctrl+Z pause)')
def chat(model_a, model_b, turns, prompt, dimensions, puzzle, experiment, topic_content, save_to, config, no_attractor_detection, manual, flowing):
    """Run a conversation between two AI agents"""
    
    # Validate conductor mode flags
    if manual and flowing:
        console.print("[red]Error: Cannot use both --manual and --flowing flags at the same time[/red]")
        raise click.Abort()
    
    # Resolve model shortcuts using the new system
    config_a = get_model_config(model_a)
    config_b = get_model_config(model_b)
    
    model_a_id = config_a.model_id if config_a else model_a
    model_b_id = config_b.model_id if config_b else model_b
    
    # Build initial prompt from dimensions and/or custom prompt
    initial_prompt = _build_initial_prompt(prompt, dimensions, puzzle, experiment, topic_content)
    
    # Create agents
    agents = {
        "agent_a": Agent(id="agent_a", model=model_a_id),
        "agent_b": Agent(id="agent_b", model=model_b_id)
    }
    
    # Create providers based on model type
    try:
        providers = {
            "agent_a": get_provider_for_model(model_a_id),
            "agent_b": get_provider_for_model(model_b_id)
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
        cfg.set('conversation.attractor_detection.enabled', False)
    
    # Setup components
    router = DirectRouter(providers)
    transcript_manager = TranscriptManager(save_to)
    engine = DialogueEngine(router, transcript_manager, cfg)
    
    # Display configuration
    console.print(f"[bold]🤖 Starting conversation: {model_a_id} ↔ {model_b_id}[/bold]")
    console.print(f"[dim]📝 Initial prompt: {initial_prompt[:50]}{'...' if len(initial_prompt) > 50 else ''}[/dim]")
    console.print(f"[dim]🔄 Max turns: {turns}[/dim]")
    
    
    # Show context management status
    context_enabled = cfg.get('context_management.enabled', True) if hasattr(cfg, 'get') else True
    if context_enabled:
        console.print(f"[dim]📏 Context tracking: [green]ON[/green][/dim]")
    else:
        console.print(f"[dim]📏 Context tracking: [red]OFF[/red][/dim]")
    
    # Show attractor detection status
    detection_enabled = cfg.get('conversation.attractor_detection.enabled', True) if hasattr(cfg, 'get') else True
    if detection_enabled:
        threshold = cfg.get('conversation.attractor_detection.threshold', 3) if hasattr(cfg, 'get') else 3
        window = cfg.get('conversation.attractor_detection.window_size', 10) if hasattr(cfg, 'get') else 10
        console.print(f"[dim]🔍 Attractor detection: [green]ON[/green] (threshold: {threshold}, window: {window})[/dim]")
    else:
        console.print(f"[dim]🔍 Attractor detection: [red]OFF[/red][/dim]")
    
    # Determine conductor mode
    conductor_mode = None
    if manual:
        conductor_mode = "manual"
        console.print(f"[dim]🎼 Conductor mode: [green]MANUAL[/green] (message-by-message control)[/dim]")
    elif flowing:
        conductor_mode = "flowing"
        console.print(f"[dim]🎼 Conductor mode: [green]FLOWING[/green] (auto-flows, Ctrl+Z to pause)[/dim]")
    
    console.rule(style="dim")
    console.print()
    
    try:
        asyncio.run(engine.run_conversation(
            agents["agent_a"],
            agents["agent_b"],
            initial_prompt,
            turns,
            conductor_mode=conductor_mode
        ))
        
        # Success exit message
        console.print()
        completion_content = "[green]✅ CONVERSATION COMPLETE[/green]\n"
        completion_content += "📁 Transcript saved successfully\n"
        
        # Check if attractor was detected
        if hasattr(engine, 'attractor_detected') and engine.attractor_detected:
            result = engine.attractor_detected
            completion_content += f"🎯 Attractor detected: {result['type']} at turn {result['turn_detected']}"
        else:
            completion_content += "🎯 All turns completed normally"
        
        console.print(Panel(
            completion_content,
            title="[bold green]Conversation Summary[/bold green]",
            border_style="green"
        ))
        console.print()
        
    except KeyboardInterrupt:
        # Interrupted exit message
        console.print()
        stopped_content = "[yellow]⏹️  CONVERSATION STOPPED[/yellow]\n"
        stopped_content += "📁 Transcript saved (partial conversation)\n"
        stopped_content += "🛑 Stopped by user (Ctrl+C)"
        
        console.print(Panel(
            stopped_content,
            title="[bold yellow]Conversation Interrupted[/bold yellow]",
            border_style="yellow"
        ))
        console.print()
        
    except Exception as e:
        # Error exit message
        console.print()
        error_content = "[red]❌ CONVERSATION ERROR[/red]\n"
        error_content += f"💥 Error: {e}\n"
        error_content += "📁 Transcript may be incomplete"
        
        console.print(Panel(
            error_content,
            title="[bold red]Conversation Error[/bold red]",
            border_style="red"
        ))
        console.print()


@cli.command()
@click.help_option('-h', '--help')
@click.option('-p', '--provider', help='Filter by provider (anthropic/openai)')
@click.option('-d', '--detailed', is_flag=True, help='Show detailed information')
def models(provider, detailed):
    """List all available models and their shortcuts"""
    
    if provider:
        # Filter by provider
        if provider.lower() not in ['anthropic', 'openai']:
            console.print(f"[red]Error: Invalid provider '{provider}'. Use 'anthropic' or 'openai'.[/red]")
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
                notes
            )
    else:
        # Simple format
        for model in models:
            # Format aliases
            aliases = ", ".join(model.aliases)
            if aliases:
                aliases = f"({aliases})"
            
            # Format context window
            context = f"[{model.context_window//1000}K]" if model.context_window > 0 else ""
            
            # Notes
            notes = f"- {model.notes}" if model.notes else ""
            if model.deprecated:
                notes = f"[red]- DEPRECATED {model.deprecation_date}[/red]"
            
            # Display line
            console.print(f"  {model.model_id:<30} {aliases:<40} {context:<8} {notes}")
    
    if detailed:
        console.print(table)


@cli.command()
@click.help_option('-h', '--help')
@click.argument('checkpoint_file', required=False, type=click.Path(exists=True))
@click.option('-l', '--latest', is_flag=True, help='Resume from the latest checkpoint')
def resume(checkpoint_file, latest):
    """Resume a paused conversation from checkpoint"""
    
    checkpoint_manager = CheckpointManager()
    
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
            if 'error' in cp:
                console.print(f"{i+1}. [red]{cp['path']} (Error: {cp['error']})[/red]")
            else:
                console.print(f"{i+1}. {cp['path']}")
                console.print(f"   [dim]Models: {cp['model_a']} vs {cp['model_b']}[/dim]")
                console.print(f"   [dim]Turn {cp['turn_count']}/{cp['max_turns']} - {cp['remaining_turns']} turns remaining[/dim]")
                console.print(f"   [dim]Paused: {cp['pause_time']}[/dim]\n")
        
        console.print("[yellow]Specify a checkpoint file or use --latest[/yellow]")
        return
    
    # Load checkpoint
    try:
        state = ConversationState.load_checkpoint(checkpoint_path)
        info = state.get_resume_info()
        
        console.print(f"\n[bold]Resuming conversation:[/bold]")
        console.print(f"Models: {info['model_a']} vs {info['model_b']}")
        console.print(f"Turn: {info['turn_count']}/{info['max_turns']}")
        console.print(f"Remaining turns: {info['remaining_turns']}\n")
        
        # Recreate agents and providers
        agents = {
            "agent_a": Agent(id=state.agent_a_id, model=state.model_a),
            "agent_b": Agent(id=state.agent_b_id, model=state.model_b)
        }
        
        providers = {
            "agent_a": get_provider_for_model(state.model_a),
            "agent_b": get_provider_for_model(state.model_b)
        }
        
        # Setup components
        router = DirectRouter(providers)
        transcript_manager = TranscriptManager()
        
        # Load config
        cfg = Config()
        
        engine = DialogueEngine(router, transcript_manager, cfg)
        
        # Resume conversation
        asyncio.run(engine.run_conversation(
            agents["agent_a"],
            agents["agent_b"],
            state.initial_prompt,
            state.max_turns,
            resume_from_state=state
        ))
        
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
@click.help_option('-h', '--help')
@click.option('--example', help='Show example for specific dimension combination')
@click.option('--list', 'list_only', is_flag=True, help='List just dimension names')
@click.option('--detailed', is_flag=True, help='Show detailed info about a dimension')
@click.argument('dimension', required=False)
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
                console.print(f"    • [yellow]{value}[/yellow] - Requires additional content")
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
        ("interview:meta:exploratory", "Exploratory interview about the conversation itself"),
        ("collaboration:thought_experiments --experiment trolley_problem", "Work together on the trolley problem"),
    ]
    
    for example_spec, description in examples:
        console.print(f"  [dim]pidgin chat -d {example_spec}[/dim]")
        console.print(f"    → {description}")
    console.print()


@cli.command()
@click.help_option('-h', '--help')
@click.option('--dimensions', is_flag=True, help='Create dimension configuration template')
@click.option('--puzzles', is_flag=True, help='Create puzzle library template')
@click.option('--experiments', is_flag=True, help='Create thought experiment library template')
@click.option('--all', 'create_all', is_flag=True, help='Create all configuration templates')
def config(dimensions, puzzles, experiments, create_all):
    """Create configuration templates for customization"""
    from datetime import datetime
    
    config_dir = Path.home() / '.pidgin'
    created_files = []
    
    # Create directory if needed
    if any([dimensions, puzzles, experiments, create_all]):
        config_dir.mkdir(exist_ok=True)
    
    # Puzzles template
    if puzzles or create_all:
        puzzle_path = config_dir / 'puzzles.yaml'
        if not puzzle_path.exists():
            puzzle_content = f'''# Pidgin Custom Puzzle Library
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
  
'''
            with open(puzzle_path, 'w') as f:
                f.write(puzzle_content)
            created_files.append(puzzle_path)
            console.print(f"[green]✓ Created {puzzle_path}[/green]")
        else:
            console.print(f"[yellow]! {puzzle_path} already exists[/yellow]")
    
    # Thought experiments template
    if experiments or create_all:
        exp_path = config_dir / 'thought_experiments.yaml'
        if not exp_path.exists():
            exp_content = f'''# Pidgin Thought Experiment Library
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
  
'''
            with open(exp_path, 'w') as f:
                f.write(exp_content)
            created_files.append(exp_path)
            console.print(f"[green]✓ Created {exp_path}[/green]")
        else:
            console.print(f"[yellow]! {exp_path} already exists[/yellow]")
    
    # Dimensions template (for future use)
    if dimensions or create_all:
        dim_path = config_dir / 'dimensions.yaml'
        if not dim_path.exists():
            dim_content = f'''# Pidgin Custom Dimensions
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
  
'''
            with open(dim_path, 'w') as f:
                f.write(dim_content)
            created_files.append(dim_path)
            console.print(f"[green]✓ Created {dim_path}[/green]")
        else:
            console.print(f"[yellow]! {dim_path} already exists[/yellow]")
    
    if not any([dimensions, puzzles, experiments, create_all]):
        console.print("\n[bold]Configuration Templates[/bold]\n")
        console.print("Create template files for customizing Pidgin:")
        console.print("  pidgin config --puzzles      Create puzzle library template")
        console.print("  pidgin config --experiments  Create thought experiment template") 
        console.print("  pidgin config --dimensions   Create custom dimensions template")
        console.print("  pidgin config --all          Create all templates\n")
    elif created_files:
        console.print(f"\n[green]Created {len(created_files)} configuration template(s) in {config_dir}[/green]")
    

if __name__ == "__main__":
    cli()