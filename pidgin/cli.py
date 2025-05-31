import click
import asyncio
import os
from rich.console import Console
from rich.markdown import Markdown
from pidgin.config import MODEL_SHORTCUTS
from .types import Agent
from .providers.anthropic import AnthropicProvider
from .router import DirectRouter
from .dialogue import DialogueEngine
from .transcripts import TranscriptManager

console = Console()


@click.group()
def cli():
    """Pidgin - AI conversation research tool"""
    pass


@cli.command()
@click.option('-a', '--agent-a', required=True, help='First agent model')
@click.option('-b', '--agent-b', required=True, help='Second agent model')
@click.option('-t', '--turns', default=10, help='Number of conversation turns')
@click.option('-p', '--prompt', default="Hello! I'm looking forward to our conversation.", help='Initial prompt')
@click.option('-s', '--save-to', help='Save transcript to specific location')
def chat(agent_a, agent_b, turns, prompt, save_to):
    """Run a conversation between two AI agents"""
    
    # Resolve model shortcuts
    model_a = MODEL_SHORTCUTS.get(agent_a, agent_a)
    model_b = MODEL_SHORTCUTS.get(agent_b, agent_b)
    
    # Create agents
    agents = {
        "agent_a": Agent(id="agent_a", model=model_a),
        "agent_b": Agent(id="agent_b", model=model_b)
    }
    
    # Create providers (Phase 1: Anthropic only)
    try:
        providers = {
            "agent_a": AnthropicProvider(model_a),
            "agent_b": AnthropicProvider(model_b)
        }
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    # Setup components
    router = DirectRouter(providers)
    transcript_manager = TranscriptManager(save_to)
    engine = DialogueEngine(router, transcript_manager)
    
    # Run conversation
    console.print(f"[bold]Starting conversation between {agent_a} and {agent_b}[/bold]\n")
    
    try:
        asyncio.run(engine.run_conversation(
            agents["agent_a"],
            agents["agent_b"],
            prompt,
            turns
        ))
        console.print("\n[green]Conversation complete! Transcript saved.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Conversation interrupted but transcript saved.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    cli()