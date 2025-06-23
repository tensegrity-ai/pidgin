# pidgin/cli/chat.py
"""Chat-related CLI commands."""

import os
import sys
import asyncio
from typing import Optional, List
from pathlib import Path

from .ollama_setup import normalize_local_model_names, ensure_ollama_models_ready

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .helpers import (
    get_provider_for_model, 
    build_initial_prompt,
    validate_model_id,
    format_model_display,
    check_ollama_available,
    parse_temperature,
    parse_dimensions
)
from .constants import (
    NORD_BLUE, NORD_YELLOW, NORD_RED, NORD_GREEN,
    DEFAULT_TURNS, DEFAULT_TEMPERATURE,
    MODEL_EMOJIS, PROVIDER_COLORS
)
from ..core import Conductor, Agent, Conversation
from ..io import OutputManager
from ..config.models import MODELS

console = Console()


@click.command()
@click.option('--agent-a', '-a', 
              help='First agent model (e.g., gpt-4, claude, gemini-1.5-pro)')
@click.option('--agent-b', '-b', 
              help='Second agent model')
@click.option('--prompt', '-p', 
              help='Initial prompt to start the conversation')
@click.option('--turns', '-t', 
              default=DEFAULT_TURNS, 
              help=f'Maximum number of conversation turns (default: {DEFAULT_TURNS})')
@click.option('--temperature', 
              type=click.FloatRange(0.0, 2.0), 
              help='Temperature for both agents (0.0-2.0)')
@click.option('--temp-a', 
              type=click.FloatRange(0.0, 2.0), 
              help='Temperature for agent A only')
@click.option('--temp-b', 
              type=click.FloatRange(0.0, 2.0), 
              help='Temperature for agent B only')
@click.option('--output', '-o', 
              help='Custom output directory')
@click.option('--dimension', '-d', 
              multiple=True, 
              help='Predefined conversation dimensions')
@click.option('--convergence-threshold', 
              type=float, 
              help='Stop when convergence score exceeds this (0.0-1.0)')
@click.option('--convergence-action', 
              type=click.Choice(['notify', 'pause', 'stop']), 
              default='notify',
              help='Action when convergence threshold is reached')
@click.option('--first-speaker', 
              type=click.Choice(['a', 'b', 'random']), 
              default='a',
              help='Which agent speaks first')
@click.option('--choose-names',
              is_flag=True,
              help='Let agents choose their own names')
@click.option('-w', '--awareness',
              type=click.Choice(['none', 'basic', 'firm', 'research']),
              default='basic',
              help='Awareness level for both agents')
@click.option('--awareness-a',
              type=click.Choice(['none', 'basic', 'firm', 'research']),
              help='Awareness level for agent A only')
@click.option('--awareness-b',
              type=click.Choice(['none', 'basic', 'firm', 'research']),
              help='Awareness level for agent B only')
@click.option('--show-system-prompts',
              is_flag=True,
              help='Display system prompts at start')
@click.option('--meditation', 
              is_flag=True, 
              help='Meditation mode: one agent faces silence')
def chat(agent_a, agent_b, prompt, turns, temperature, temp_a, 
         temp_b, output, dimension, convergence_threshold,
         convergence_action, first_speaker, choose_names, awareness,
         awareness_a, awareness_b, show_system_prompts, meditation):
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

    [#4c566a]Meditation mode (one agent contemplates in silence):[/#4c566a]
        pidgin chat -a claude --meditation
    """
    # Handle meditation mode
    if meditation:
        if not agent_a:
            agent_a = "claude"
        if not agent_b:
            agent_b = "silent"
        console.print(f"\n[{NORD_BLUE}]◆ Meditation mode: {agent_a} → silence[/{NORD_BLUE}]")
    
    model_a, model_b = asyncio.run(normalize_local_model_names(model_a, model_b, console))

    # Interactive model selection if not provided
    if not agent_a:
        agent_a = _prompt_for_model("Select first agent (Agent A)")
        if not agent_a:
            return
    
    if not agent_b:
        agent_b = _prompt_for_model("Select second agent (Agent B)")
        if not agent_b:
            return
    
    # Validate models
    try:
        agent_a_id, agent_a_name = validate_model_id(agent_a)
        agent_b_id, agent_b_name = validate_model_id(agent_b)
    except ValueError as e:
        console.print(f"[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        return
    
    if not asyncio.run(ensure_ollama_models_ready(model_a, model_b, console)):
        raise click.Abort()

    # Handle temperature settings
    temp_a = temperature_a if temperature_a is not None else temperature
    temp_b = temperature_b if temperature_b is not None else temperature
    
    # Build initial prompt
    initial_prompt = build_initial_prompt(prompt, list(dimension))
    
    # Show configuration
    console.print(f"\n[bold {NORD_BLUE}]◆ Starting Conversation[/bold {NORD_BLUE}]")
    console.print(f"  {format_model_display(agent_a_id)} ↔ {format_model_display(agent_b_id)}")
    console.print(f"  Max turns: {turns}")
    console.print(f"  Initial prompt: {initial_prompt[:100]}{'...' if len(initial_prompt) > 100 else ''}")
    
    if temp_a is not None or temp_b is not None:
        temp_str = []
        if temp_a is not None:
            temp_str.append(f"A: {temp_a}")
        if temp_b is not None:
            temp_str.append(f"B: {temp_b}")
        console.print(f"  Temperature: {', '.join(temp_str)}")
    
    if convergence_threshold:
        console.print(f"  Convergence: {convergence_threshold} → {convergence_action}")
    
    # Determine first speaker
    if first_speaker == 'random':
        import random
        first_speaker = random.choice(['a', 'b'])
    first_speaker_id = f"agent_{first_speaker}"
    
    console.print(f"  First speaker: Agent {first_speaker.upper()}")
    console.print()
    
    # Run the conversation
    try:
        asyncio.run(_run_conversation(
            agent_a_id, agent_b_id, 
            agent_a_name, agent_b_name,
            initial_prompt, turns,
            temp_a, temp_b,
            output, convergence_threshold, convergence_action,
            first_speaker_id
        ))
    except KeyboardInterrupt:
        console.print(f"\n[{NORD_YELLOW}]Conversation interrupted by user[/{NORD_YELLOW}]")
    except Exception as e:
        console.print(f"\n[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        if "rate limit" in str(e).lower():
            console.print(f"[{NORD_YELLOW}]Tip: Try reducing temperature or adding delays[/{NORD_YELLOW}]")


async def _run_conversation(agent_a_id: str, agent_b_id: str,
                          agent_a_name: str, agent_b_name: str,
                          initial_prompt: str, max_turns: int,
                          temp_a: Optional[float], temp_b: Optional[float],
                          output_dir: Optional[str],
                          convergence_threshold: Optional[float],
                          convergence_action: str,
                          first_speaker: str):
    """Run the actual conversation."""
    # Create providers
    provider_a = await get_provider_for_model(agent_a_id, temp_a)
    provider_b = await get_provider_for_model(agent_b_id, temp_b)
    
    # Create agents
    agent_a = Agent(
        id="agent_a",
        model=agent_a_id,
        display_name=agent_a_name,
        temperature=temp_a
    )
    
    agent_b = Agent(
        id="agent_b",
        model=agent_b_id,
        display_name=agent_b_name,
        temperature=temp_b
    )
    
    # Set up providers
    providers = {
        "agent_a": provider_a,
        "agent_b": provider_b
    }
    
    # Create output manager
    output_manager = OutputManager(base_dir=output_dir)
    
    # Create conductor
    conductor = Conductor(
        providers=providers,
        output_manager=output_manager,
        convergence_threshold=convergence_threshold,
        convergence_action=convergence_action
    )
    
    # Run conversation
    await conductor.run_conversation(
        agent_a=agent_a,
        agent_b=agent_b,
        initial_prompt=initial_prompt,
        max_turns=max_turns,
        first_speaker=first_speaker
    )


def _prompt_for_model(prompt_text: str) -> Optional[str]:
    """Interactive model selection."""
    console.print(f"\n[bold {NORD_BLUE}]{prompt_text}:[/bold {NORD_BLUE}]")
    
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
    
    for provider in ['openai', 'anthropic', 'google', 'xai', 'local']:
        if provider not in providers:
            continue
            
        console.print(f"\n[{PROVIDER_COLORS.get(provider, 'white')}]{provider.title()}:[/{PROVIDER_COLORS.get(provider, 'white')}]")
        
        for model_id, config in providers[provider]:
            emoji = MODEL_EMOJIS.get(model_id, "🤖")
            console.print(f"  {idx}. {emoji} {config.display_name}")
            model_map[str(idx)] = model_id
            idx += 1
    
    # Add option for custom local model
    console.print(f"\n[{NORD_YELLOW}]Other:[/{NORD_YELLOW}]")
    console.print(f"  {idx}. 🔧 Custom local model (requires Ollama)")
    
    # Get selection
    selection = console.input(f"\n[{NORD_BLUE}]Enter selection (1-{idx}) or model name: [/{NORD_BLUE}]")
    
    if selection in model_map:
        return model_map[selection]
    elif selection == str(idx):
        # Custom local model
        if not check_ollama_available():
            console.print(f"[{NORD_RED}]Error: Ollama is not running. Start it with 'ollama serve'[/{NORD_RED}]")
            return None
        model_name = console.input(f"[{NORD_BLUE}]Enter local model name: [/{NORD_BLUE}]")
        return f"local:{model_name}"
    else:
        # Try as direct model ID
        try:
            validate_model_id(selection)
            return selection
        except ValueError:
            console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
            return None


@click.command()
@click.option('--provider', '-p', 
              type=click.Choice(['all', 'openai', 'anthropic', 'google', 'xai', 'local']),
              default='all',
              help='Filter models by provider')
@click.option('--format', '-f',
              type=click.Choice(['table', 'list', 'json']),
              default='table',
              help='Output format')
def models(provider, format):
    """Display available AI models organized by provider.

    Shows all supported models with their aliases, context windows,
    and key characteristics.
    """
    # Filter models by provider
    models_to_show = {}
    for model_id, config in MODELS.items():
        if provider == 'all' or config.provider == provider:
            models_to_show[model_id] = config
    
    if format == 'json':
        import json
        output = {}
        for model_id, config in models_to_show.items():
            output[model_id] = {
                'provider': config.provider,
                'model': config.model,
                'display_name': config.display_name,
                'temperature': config.temperature,
                'emoji': MODEL_EMOJIS.get(model_id, '🤖')
            }
        console.print_json(data=output)
        return
    
    if format == 'list':
        for model_id, config in models_to_show.items():
            emoji = MODEL_EMOJIS.get(model_id, '🤖')
            color = PROVIDER_COLORS.get(config.provider, 'white')
            console.print(f"{emoji} [{color}]{model_id}[/{color}] - {config.display_name}")
        return
    
    # Table format
    table = Table(title="Available Models" if provider == 'all' else f"{provider.title()} Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Display Name", style="white")
    table.add_column("Provider", style="yellow")
    table.add_column("Temperature", style="green")
    
    # Group by provider for better display
    by_provider = {}
    for model_id, config in models_to_show.items():
        if config.provider not in by_provider:
            by_provider[config.provider] = []
        by_provider[config.provider].append((model_id, config))
    
    # Sort providers
    for prov in ['openai', 'anthropic', 'google', 'xai', 'local']:
        if prov not in by_provider:
            continue
            
        # Add provider separator
        if len(by_provider) > 1 and provider == 'all':
            table.add_row("", f"[bold {PROVIDER_COLORS.get(prov, 'white')}]── {prov.title()} ──[/bold {PROVIDER_COLORS.get(prov, 'white')}]", "", "")
        
        # Add models
        for model_id, config in sorted(by_provider[prov], key=lambda x: x[0]):
            emoji = MODEL_EMOJIS.get(model_id, '🤖')
            table.add_row(
                f"{emoji} {model_id}",
                config.shortname,
                config.provider,
            )
    
    console.print(table)
    
    # Show additional info
    console.print(f"\n[{NORD_BLUE}]To use a model:[/{NORD_BLUE}]")
    console.print(f"  pidgin chat -a <model-id> -b <model-id>")
    console.print(f"\n[{NORD_BLUE}]For local models with Ollama:[/{NORD_BLUE}]")
    console.print(f"  pidgin chat -a local:llama3.1 -b local:mistral")
