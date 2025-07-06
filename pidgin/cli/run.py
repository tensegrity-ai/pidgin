# pidgin/cli/run.py
"""Unified run command for conversations and experiments."""

import os
import sys
import asyncio
import uuid
import signal
from typing import Optional, List
from pathlib import Path
from datetime import datetime

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .ollama_setup import normalize_local_model_names, ensure_ollama_models_ready
from .helpers import (
    get_provider_for_model, 
    build_initial_prompt,
    validate_model_id,
    format_model_display,
    check_ollama_available,
    parse_temperature,
    parse_dimensions
)
from ..config.resolution import resolve_temperatures
from ..config.defaults import get_smart_convergence_defaults
from .constants import (
    NORD_BLUE, NORD_YELLOW, NORD_RED, NORD_GREEN, NORD_CYAN,
    DEFAULT_TURNS, DEFAULT_TEMPERATURE,
    MODEL_EMOJIS, PROVIDER_COLORS
)
from ..core import Conductor, Agent, Conversation
from ..io import OutputManager
from ..io.paths import get_experiments_dir
from ..config.models import MODELS, get_model_config
from .notify import send_notification
from ..experiments import ExperimentManager, ExperimentConfig, ExperimentRunner
from .experiment_utils import attach_to_experiment

console = Console()

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD


@click.command()
@click.option('--agent-a', '-a', 
              help='First agent model (e.g., gpt-4, claude, gemini-1.5-pro)')
@click.option('--agent-b', '-b', 
              help='Second agent model')
@click.option('--prompt', '-p', 
              help='Initial prompt to start the conversation')
@click.option('--turns', '-t', 
              type=click.IntRange(1, 1000),
              default=DEFAULT_TURNS, 
              help=f'Maximum number of conversation turns (default: {DEFAULT_TURNS})')
@click.option('--repetitions', '-r',
              type=click.IntRange(1, 10000),
              default=1,
              help='Number of conversations to run (default: 1)')
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
@click.option('--quiet', '-q',
              is_flag=True,
              help='Minimal output (start, turn progress, end)')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Show all events for debugging')
@click.option('--notify', '-n',
              is_flag=True,
              help='Send notification when complete')
@click.option('--name',
              help='Name for the experiment (required for multiple runs)')
@click.option('--max-parallel',
              type=click.IntRange(1, 50),
              default=1,
              help='Max parallel conversations (default: 1, sequential)')
@click.option('--foreground',
              is_flag=True,
              help='Run in foreground (even for multiple repetitions)')
@click.option('--background',
              is_flag=True,
              help='Run in background (even for single conversation)')
@click.option('--detach',
              is_flag=True,
              help='Start in background without attaching')
def run(agent_a, agent_b, prompt, turns, repetitions, temperature, temp_a, 
        temp_b, output, dimension, convergence_threshold,
        convergence_action, first_speaker, choose_names, awareness,
        awareness_a, awareness_b, show_system_prompts, meditation,
        quiet, verbose, notify, name, max_parallel, foreground, background, detach):
    """Run AI conversations - single or multiple.

    This unified command runs conversations between two AI agents.
    Single conversations run in foreground by default.
    Multiple conversations run as background experiments by default.

    [bold]EXAMPLES:[/bold]

    [#4c566a]Single conversation (foreground):[/#4c566a]
        pidgin run -a claude -b gpt
        pidgin run -a opus -b gpt-4.1 -t 50 -p "What is consciousness?"

    [#4c566a]Multiple conversations (background):[/#4c566a]
        pidgin run -a claude -b gpt -r 20 --name "test"
        pidgin run -a claude -b gpt -r 100 --name "long" --detach

    [#4c566a]Using dimensional prompts:[/#4c566a]
        pidgin run -a claude -b gpt -d peers:philosophy
        pidgin run -a gpt -b gemini -d debate:language:analytical

    [#4c566a]Let agents name themselves:[/#4c566a]
        pidgin run -a claude -b gpt --choose-names

    [#4c566a]High convergence monitoring:[/#4c566a]
        pidgin run -a claude -b gpt -t 100 --convergence-threshold 0.8

    [#4c566a]Different awareness levels:[/#4c566a]
        pidgin run -a claude -b gpt --awareness research
        pidgin run -a claude -b gpt --awareness-a firm --awareness-b none

    [#4c566a]Meditation mode:[/#4c566a]
        pidgin run -a claude --meditation

    [#4c566a]Force foreground for multiple:[/#4c566a]
        pidgin run -a claude -b gpt -r 10 --foreground

    [#4c566a]Force background for single:[/#4c566a]
        pidgin run -a claude -b gpt --background --name "single"
    """
    # Handle display mode flags
    if quiet and verbose:
        console.print(f"[{NORD_RED}]Error: Cannot use both --quiet and --verbose[/{NORD_RED}]")
        return
    
    display_mode = "normal"
    if quiet:
        display_mode = "quiet"
    elif verbose:
        display_mode = "verbose"
    
    # Handle meditation mode
    if meditation:
        if not agent_a:
            agent_a = "claude"
        if not agent_b:
            agent_b = "silent"
        console.print(f"\n[{NORD_BLUE}]◆ Meditation mode: {agent_a} → silence[/{NORD_BLUE}]")
    
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

    # Handle temperature settings
    temp_a, temp_b = resolve_temperatures(temperature, temp_a, temp_b)
    
    # Build initial prompt
    initial_prompt = build_initial_prompt(prompt, list(dimension))
    
    # Add smart convergence defaults for API models
    if convergence_threshold is None:
        default_threshold, default_action = get_smart_convergence_defaults(agent_a_id, agent_b_id)
        if default_threshold is not None:
            convergence_threshold = default_threshold
            if convergence_action is None:
                convergence_action = default_action
            # Log this default
            console.print(f"[dim]Using default convergence threshold: {convergence_threshold} → {convergence_action}[/dim]")
    
    # Default convergence action
    if convergence_action is None:
        convergence_action = 'stop' if repetitions > 1 else 'notify'
    
    # Determine execution mode
    is_single = repetitions == 1
    run_in_foreground = (is_single and not background) or foreground
    
    # Validate name requirement
    if not is_single and not name:
        # Auto-generate name for multiple runs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{agent_a}_{agent_b}_{timestamp}"
        console.print(f"[dim]Auto-generated experiment name: {name}[/dim]")
    elif is_single and not name and background:
        # Need name for background single runs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"single_{agent_a}_{agent_b}_{timestamp}"
    
    # Determine first speaker
    if first_speaker == 'random':
        import random
        first_speaker = random.choice(['a', 'b'])
    first_speaker_id = f"agent_{first_speaker}"
    
    # Run based on mode
    if is_single and run_in_foreground:
        # Single conversation in foreground (classic chat mode)
        try:
            asyncio.run(_run_single_conversation(
                agent_a_id, agent_b_id, 
                agent_a_name, agent_b_name,
                initial_prompt, turns,
                temp_a, temp_b,
                output, convergence_threshold, convergence_action,
                first_speaker_id, display_mode
            ))
            
            # Send notification if requested
            if notify:
                send_notification(
                    title="Pidgin Conversation Complete",
                    message=f"Conversation between {agent_a_name} and {agent_b_name} has finished ({turns} turns)"
                )
            
        except KeyboardInterrupt:
            console.print(f"\n[{NORD_YELLOW}]Conversation interrupted by user[/{NORD_YELLOW}]")
        except Exception as e:
            console.print(f"\n[{NORD_RED}]Error: {e}[/{NORD_RED}]")
            if "rate limit" in str(e).lower():
                console.print(f"[{NORD_YELLOW}]Tip: Try reducing temperature or adding delays[/{NORD_YELLOW}]")
    
    else:
        # Multiple conversations or background single - run as experiment
        _run_as_experiment(
            agent_a_id, agent_b_id,
            agent_a_name, agent_b_name,
            repetitions, turns,
            temp_a, temp_b,
            initial_prompt, dimension,
            name, max_parallel,
            convergence_threshold, convergence_action,
            awareness, awareness_a, awareness_b,
            choose_names, run_in_foreground, detach, notify
        )


async def _run_single_conversation(agent_a_id: str, agent_b_id: str,
                                 agent_a_name: str, agent_b_name: str,
                                 initial_prompt: str, max_turns: int,
                                 temp_a: Optional[float], temp_b: Optional[float],
                                 output_dir: Optional[str],
                                 convergence_threshold: Optional[float],
                                 convergence_action: str,
                                 first_speaker: str,
                                 display_mode: str = "normal"):
    """Run a single conversation in foreground."""
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
        output_manager=output_manager,
        console=console,
        base_providers=providers,
        convergence_threshold_override=convergence_threshold,
        convergence_action_override=convergence_action
    )
    
    # Run conversation
    await conductor.run_conversation(
        agent_a=agent_a,
        agent_b=agent_b,
        initial_prompt=initial_prompt,
        max_turns=max_turns,
        display_mode=display_mode,
    )


def _run_as_experiment(agent_a_id, agent_b_id, agent_a_name, agent_b_name,
                      repetitions, max_turns, temp_a, temp_b,
                      initial_prompt, dimensions, name, max_parallel,
                      convergence_threshold, convergence_action,
                      awareness, awareness_a, awareness_b,
                      choose_names, run_in_foreground, detach, notify):
    """Run as an experiment (multiple conversations or background)."""
    # Create experiment configuration
    config = ExperimentConfig(
        name=name,
        agent_a_model=agent_a_id,
        agent_b_model=agent_b_id,
        repetitions=repetitions,
        max_turns=max_turns,
        temperature_a=temp_a,
        temperature_b=temp_b,
        custom_prompt=initial_prompt if initial_prompt != "Hello" else None,
        dimensions=list(dimensions) if dimensions else None,
        max_parallel=max_parallel,
        convergence_threshold=convergence_threshold,
        convergence_action=convergence_action,
        awareness=awareness,
        awareness_a=awareness_a,
        awareness_b=awareness_b,
        choose_names=choose_names
    )
    
    # Show configuration
    console.print(f"\n[bold {NORD_BLUE}]◆ Experiment Configuration[/bold {NORD_BLUE}]")
    console.print(f"  Name: {name}")
    console.print(f"  Models: {format_model_display(agent_a_id)} ↔ {format_model_display(agent_b_id)}")
    console.print(f"  Conversations: {repetitions}")
    console.print(f"  Turns per conversation: {max_turns}")
    console.print(f"  Parallel execution: {max_parallel}")
    
    if initial_prompt != "Hello":
        console.print(f"  Initial prompt: {initial_prompt[:50]}...")
    
    if temp_a is not None or temp_b is not None:
        temp_parts = []
        if temp_a is not None:
            temp_parts.append(f"A: {temp_a}")
        if temp_b is not None:
            temp_parts.append(f"B: {temp_b}")
        console.print(f"  Temperature: {', '.join(temp_parts)}")
    
    if convergence_threshold:
        console.print(f"  Convergence: {convergence_threshold} → {convergence_action}")
    
    # Check if experiment already exists
    from .jsonl_reader import JSONLExperimentReader
    jsonl_reader = JSONLExperimentReader(get_experiments_dir())
    experiments = jsonl_reader.list_experiments()
    existing = next((exp for exp in experiments if exp.get('name') == name), None)

    if existing:
        console.print(f"[#bf616a]Experiment session '{name}' already exists[/#bf616a]")
        console.print(f"Use 'pidgin attach {name}' to monitor")
        return
    
    # Validate configuration
    errors = config.validate()
    if errors:
        console.print(f"[#bf616a]Configuration errors:[/#bf616a]")
        for error in errors:
            console.print(f"  • {error}")
        return
    
    if run_in_foreground:
        # Run in foreground (debug mode)
        console.print(f"[#ebcb8b]◆ Starting '{name}' in foreground[/#ebcb8b]")
        console.print(f"[#4c566a]  Models: {agent_a_name} vs {agent_b_name}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        console.print(f"\n[#bf616a]Running in foreground - press Ctrl+C to stop[/#bf616a]\n")
        
        # Run directly without daemon
        runner = ExperimentRunner(get_experiments_dir(), daemon=None)
        
        # Generate experiment ID
        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        
        async def run_foreground_experiment():
            try:
                await runner.run_experiment_with_id(exp_id, config)
                return True
            except Exception:
                raise
        
        try:
            success = asyncio.run(run_foreground_experiment())
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' completed[/#a3be8c]")
            if notify:
                send_notification(
                    title="Pidgin Experiment Complete",
                    message=f"Experiment '{name}' has finished ({repetitions} conversations)"
                )
            else:
                # Terminal bell notification
                print('\a', end='', flush=True)
        except KeyboardInterrupt:
            console.print(f"\n[#ebcb8b]Experiment interrupted by user[/#ebcb8b]")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Experiment failed: {e}[/#bf616a]")
            import traceback
            traceback.print_exc()
            # Terminal bell for failure too
            print('\a', end='', flush=True)
    else:
        # Run as daemon (background)
        base_dir = get_experiments_dir()
        manager = ExperimentManager(base_dir=base_dir)
        
        console.print(f"[#8fbcbb]◆ Starting experiment '{name}'[/#8fbcbb]")
        console.print(f"[#4c566a]  Models: {agent_a_name} vs {agent_b_name}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        
        try:
            # Use the original working directory captured at module import
            exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
            
            # Show start message
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' started successfully[/#a3be8c]")
            
            if detach:
                # User wants to detach - just show info
                console.print(f"[#4c566a]Running in background. Use 'pidgin attach {exp_id[:8]}' to monitor[/#4c566a]")
            else:
                # Default behavior: automatically attach to show progress
                console.print(f"[#4c566a]Attaching to experiment...[/#4c566a]\n")
                
                # Give the daemon a moment to start
                import time
                time.sleep(2)
                
                # Get the experiment directory
                exp_dir = get_experiments_dir() / exp_id
                
                # Attach to the experiment
                try:
                    asyncio.run(attach_to_experiment(exp_id, tail=False, exp_dir=exp_dir))
                except KeyboardInterrupt:
                    # Already handled in attach_to_experiment
                    pass
                
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Failed to start experiment: {str(e)}[/#bf616a]")
            raise


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