import click
import asyncio
import os
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
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

console = Console()


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
@click.option('-a', '--agent-a', required=True, help='First agent model')
@click.option('-b', '--agent-b', required=True, help='Second agent model')
@click.option('-t', '--turns', default=10, help='Number of conversation turns')
@click.option('-p', '--prompt', default="Hello! I'm looking forward to our conversation.", help='Initial prompt')
@click.option('-s', '--save-to', help='Save transcript to specific location')
@click.option('-c', '--config', type=click.Path(exists=True), help='Path to config file')
@click.option('-n', '--no-attractor-detection', '--no-detection', is_flag=True, help='Disable attractor detection')
def chat(agent_a, agent_b, turns, prompt, save_to, config, no_attractor_detection):
    """Run a conversation between two AI agents"""
    
    # Resolve model shortcuts using the new system
    config_a = get_model_config(agent_a)
    config_b = get_model_config(agent_b)
    
    model_a = config_a.model_id if config_a else agent_a
    model_b = config_b.model_id if config_b else agent_b
    
    # Create agents
    agents = {
        "agent_a": Agent(id="agent_a", model=model_a),
        "agent_b": Agent(id="agent_b", model=model_b)
    }
    
    # Create providers based on model type
    try:
        providers = {
            "agent_a": get_provider_for_model(model_a),
            "agent_b": get_provider_for_model(model_b)
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
    console.print(f"[bold]🤖 Starting conversation: {model_a} ↔ {model_b}[/bold]")
    console.print(f"[dim]📝 Initial prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}[/dim]")
    console.print(f"[dim]🔄 Max turns: {turns}[/dim]")
    
    # Show attractor detection status
    detection_enabled = cfg.get('conversation.attractor_detection.enabled', True) if hasattr(cfg, 'get') else True
    if detection_enabled:
        threshold = cfg.get('conversation.attractor_detection.threshold', 3) if hasattr(cfg, 'get') else 3
        window = cfg.get('conversation.attractor_detection.window_size', 10) if hasattr(cfg, 'get') else 10
        console.print(f"[dim]🔍 Attractor detection: [green]ON[/green] (threshold: {threshold}, window: {window})[/dim]")
    else:
        console.print(f"[dim]🔍 Attractor detection: [red]OFF[/red][/dim]")
    
    console.print(f"[dim]{'='*60}[/dim]\n")
    
    try:
        asyncio.run(engine.run_conversation(
            agents["agent_a"],
            agents["agent_b"],
            prompt,
            turns
        ))
        
        # Success exit message
        console.print("\n[green]" + "="*60 + "[/green]")
        console.print("[green bold]✅ CONVERSATION COMPLETE[/green bold]")
        console.print("[green]" + "="*60 + "[/green]")
        console.print("[green]📁 Transcript saved successfully[/green]")
        console.print("[green]🎯 All turns completed normally[/green]")
        console.print("[green]" + "="*60 + "[/green]\n")
        
    except KeyboardInterrupt:
        # Interrupted exit message
        console.print("\n[yellow]" + "="*60 + "[/yellow]")
        console.print("[yellow bold]⏹️  CONVERSATION STOPPED[/yellow bold]")
        console.print("[yellow]" + "="*60 + "[/yellow]")
        console.print("[yellow]📁 Transcript saved (partial conversation)[/yellow]")
        console.print("[yellow]🛑 Stopped by user (Ctrl+C)[/yellow]")
        console.print("[yellow]" + "="*60 + "[/yellow]\n")
        
    except Exception as e:
        # Error exit message
        console.print("\n[red]" + "="*60 + "[/red]")
        console.print("[red bold]❌ CONVERSATION ERROR[/red bold]")
        console.print("[red]" + "="*60 + "[/red]")
        console.print(f"[red]💥 Error: {e}[/red]")
        console.print("[red]📁 Transcript may be incomplete[/red]")
        console.print("[red]" + "="*60 + "[/red]\n")


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
        console.print("\n[green]" + "="*60 + "[/green]")
        console.print("[green bold]✅ RESUMED CONVERSATION COMPLETE[/green bold]")
        console.print("[green]" + "="*60 + "[/green]")
        console.print("[green]📁 Transcript updated successfully[/green]")
        console.print("[green]🔄 Conversation resumed and finished[/green]")
        console.print("[green]" + "="*60 + "[/green]\n")
        
    except FileNotFoundError:
        # File not found error
        console.print(f"\n[red]" + "="*60 + "[/red]")
        console.print("[red bold]❌ CHECKPOINT NOT FOUND[/red bold]")
        console.print("[red]" + "="*60 + "[/red]")
        console.print(f"[red]📂 File: {checkpoint_path}[/red]")
        console.print("[red]💡 Use 'pidgin resume' to list available checkpoints[/red]")
        console.print("[red]" + "="*60 + "[/red]\n")
        
    except Exception as e:
        # General resume error
        console.print(f"\n[red]" + "="*60 + "[/red]")
        console.print("[red bold]❌ RESUME ERROR[/red bold]")
        console.print("[red]" + "="*60 + "[/red]")
        console.print(f"[red]💥 Error: {e}[/red]")
        console.print("[red]🔧 Try checking the checkpoint file format[/red]")
        console.print("[red]" + "="*60 + "[/red]\n")


if __name__ == "__main__":
    cli()