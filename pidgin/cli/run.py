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
from .name_generator import generate_experiment_name
from ..core import Conductor, Agent, Conversation
from ..io import OutputManager
from ..io.paths import get_experiments_dir
from ..config.models import MODELS, get_model_config
from .notify import send_notification
from ..experiments import ExperimentManager, ExperimentConfig, ExperimentRunner

console = Console()

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD


@click.command()
@click.option('--agent-a', '-a', 
              help='* First agent model (e.g., gpt-4, claude, gemini-1.5-pro)')
@click.option('--agent-b', '-b', 
              help='* Second agent model')
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
@click.option('--convergence-profile',
              type=click.Choice(['balanced', 'structural', 'semantic', 'strict']),
              default='balanced',
              help='Convergence weight profile (default: balanced)')
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
              help='Run in background with notification when complete')
@click.option('--tail',
              is_flag=True,
              help='Show raw event stream during conversation')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Show full messages with minimal metadata')
@click.option('--notify',
              is_flag=True,
              help='Send notification when complete')
@click.option('--name', '-n',
              help='Name for the experiment (auto-generated if not provided)')
@click.option('--max-parallel',
              type=click.IntRange(1, 50),
              default=1,
              help='Max parallel conversations (default: 1, sequential)')
def run(agent_a, agent_b, prompt, turns, repetitions, temperature, temp_a, 
        temp_b, output, dimension, convergence_threshold,
        convergence_action, convergence_profile, first_speaker, choose_names, awareness,
        awareness_a, awareness_b, show_system_prompts, meditation,
        quiet, tail, verbose, notify, name, max_parallel):
    """Run AI conversations - single or multiple.

    This unified command runs conversations between two AI agents.
    By default shows a centered progress panel with key metrics.

    [bold]EXAMPLES:[/bold]

    [#4c566a]Basic conversation: [/#4c566a]
      pidgin run -a claude -b gpt

    [#4c566a]Show raw events: [/#4c566a]
      pidgin run -a claude -b gpt --tail

    [#4c566a]Run in background:  [/#4c566a]
      pidgin run -a claude -b gpt --quiet

    [#4c566a]Multiple runs:      [/#4c566a]
      pidgin run -a claude -b gpt -r 20 -n "test"

    [#4c566a]Dimensional prompt: [/#4c566a]
      pidgin run -a claude -b gpt -d philosophy

    [#4c566a]Meditation mode:    [/#4c566a]
      pidgin run -a claude --meditation
    """
    # Handle display mode flags
    mode_count = sum([quiet, tail, verbose])
    if mode_count > 1:
        console.print(f"[{NORD_RED}]Error: Can only use one of --quiet, --tail, or --verbose[/{NORD_RED}]")
        return
    
    if quiet:
        display_mode = "quiet"
        # Quiet mode should run in background and notify
        background = True
        notify = True
    elif tail:
        display_mode = "tail"  # Show raw events
    elif verbose:
        display_mode = "verbose"  # Show messages only
    else:
        display_mode = "progress"  # New default: centered progress panel
    
    # Handle meditation mode
    if meditation:
        if not agent_a:
            agent_a = "claude"
        if not agent_b:
            agent_b = "silent"
        console.print(f"\n[{NORD_BLUE}]◆ Meditation mode: {agent_a} → silence[/{NORD_BLUE}]")
    
    # Interactive model selection if not provided
    if not agent_a:
        try:
            agent_a = _prompt_for_model("Select first agent (Agent A)")
            if not agent_a:
                return
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{NORD_YELLOW}]Model selection cancelled. Use -a and -b flags to specify models.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_YELLOW}]Example: pidgin run -a claude -b gpt[/{NORD_YELLOW}]")
            return
        except Exception as e:
            console.print(f"\n[{NORD_RED}]Error during model selection: {e}[/{NORD_RED}]")
            console.print(f"[{NORD_YELLOW}]Use -a and -b flags to specify models directly.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_YELLOW}]Example: pidgin run -a claude -b gpt[/{NORD_YELLOW}]")
            return
    
    if not agent_b:
        try:
            agent_b = _prompt_for_model("Select second agent (Agent B)")
            if not agent_b:
                return
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{NORD_YELLOW}]Model selection cancelled. Use -a and -b flags to specify models.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_YELLOW}]Example: pidgin run -a claude -b gpt[/{NORD_YELLOW}]")
            return
        except Exception as e:
            console.print(f"\n[{NORD_RED}]Error during model selection: {e}[/{NORD_RED}]")
            console.print(f"[{NORD_YELLOW}]Use -a and -b flags to specify models directly.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_YELLOW}]Example: pidgin run -a claude -b gpt[/{NORD_YELLOW}]")
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
    
    # Set convergence profile in config
    from ..config import get_config
    config = get_config()
    config.set("convergence.profile", convergence_profile)
    
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
        convergence_action = 'stop'  # Always use 'stop' as default
    
    # Determine execution mode
    is_single = repetitions == 1
    
    # Determine if we run in foreground
    if quiet:
        run_in_foreground = False  # --quiet always means background
    elif max_parallel > 1:
        run_in_foreground = False  # Parallel execution requires background
        console.print(f"[{NORD_YELLOW}]Note: Parallel execution (max_parallel={max_parallel}) runs in background[/{NORD_YELLOW}]")
    else:
        # Default behavior: foreground for single conversations
        run_in_foreground = True
    
    # Generate fun name if not provided
    if not name:
        name = generate_experiment_name()
        console.print(f"[dim]Generated experiment name: {name}[/dim]")
    
    # Determine first speaker
    if first_speaker == 'random':
        import random
        first_speaker = random.choice(['a', 'b'])
    first_speaker_id = f"agent_{first_speaker}"
    
    # Always use the unified execution path
    _run_conversations(
        agent_a_id, agent_b_id,
        agent_a_name, agent_b_name,
        repetitions, turns,
        temp_a, temp_b,
        initial_prompt, dimension,
        name, max_parallel,
        convergence_threshold, convergence_action,
        awareness, awareness_a, awareness_b,
        choose_names, run_in_foreground, notify,
        display_mode, first_speaker_id, output
    )



def _run_conversations(agent_a_id, agent_b_id, agent_a_name, agent_b_name,
                      repetitions, max_turns, temp_a, temp_b,
                      initial_prompt, dimensions, name, max_parallel,
                      convergence_threshold, convergence_action,
                      awareness, awareness_a, awareness_b,
                      choose_names, run_in_foreground, notify,
                      display_mode, first_speaker_id, output_dir):
    """Run conversations using the unified execution path."""
    # Determine display mode for experiments
    # For parallel execution or background, we can't use interactive displays
    if max_parallel > 1 or not run_in_foreground:
        experiment_display_mode = 'none'
        if display_mode in ['tail', 'verbose', 'progress'] and max_parallel > 1:
            console.print(f"[{NORD_YELLOW}]Note: --{display_mode} is not supported with parallel execution[/{NORD_YELLOW}]")
    else:
        # Single conversation in foreground can use any display mode
        experiment_display_mode = display_mode
    
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
        choose_names=choose_names,
        first_speaker=first_speaker_id,
        display_mode=experiment_display_mode
    )
    
    # Show configuration
    console.print(f"\n[bold {NORD_BLUE}]◆ Experiment Configuration[/bold {NORD_BLUE}]")
    console.print(f"  Name: {name}")
    console.print(f"  Models: {format_model_display(agent_a_id)} ↔ {format_model_display(agent_b_id)}")
    console.print(f"  Conversations: {repetitions}")
    console.print(f"  Turns per conversation: {max_turns}")
    if max_parallel > 1:
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
    from ..io.jsonl_reader import JSONLExperimentReader
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
        if name:
            console.print(f"[#ebcb8b]◆ Starting '{name}' in foreground[/#ebcb8b]")
        else:
            console.print(f"[#ebcb8b]◆ Starting experiment in foreground[/#ebcb8b]")
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
            if name:
                console.print(f"\n[#a3be8c][OK] Experiment '{name}' completed[/#a3be8c]")
            else:
                console.print(f"\n[#a3be8c][OK] Experiment completed[/#a3be8c]")
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
            console.print(f"\n[#bf616a][FAIL] Experiment failed: {e}[/#bf616a]")
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
            console.print(f"\n[#a3be8c][OK] Experiment '{name}' started successfully[/#a3be8c]")
            
            # Show where to find logs
            console.print(f"[#4c566a]Running in background. Check progress:[/#4c566a]")
            console.print(f"[#4c566a]  pidgin status {exp_id[:8]}[/#4c566a]")
            console.print(f"[#4c566a]  tail -f {get_experiments_dir()}/{exp_id}/*.jsonl[/#4c566a]")
                
        except Exception as e:
            console.print(f"\n[#bf616a][FAIL] Failed to start experiment: {str(e)}[/#bf616a]")
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
            glyph = MODEL_EMOJIS.get(model_id, "●")
            console.print(f"  {idx}. {glyph} {config.shortname}")
            model_map[str(idx)] = model_id
            idx += 1
    
    # Add option for custom local model
    console.print(f"\n[{NORD_YELLOW}]Other:[/{NORD_YELLOW}]")
    console.print(f"  {idx}. ▸ Custom local model (requires Ollama)")
    
    # Get selection
    try:
        selection = console.input(f"\n[{NORD_BLUE}]Enter selection (1-{idx}) or model name: [/{NORD_BLUE}]")
    except (KeyboardInterrupt, EOFError):
        # User cancelled
        return None
    
    if selection in model_map:
        return model_map[selection]
    elif selection == str(idx):
        # Custom local model
        if not check_ollama_available():
            console.print(f"[{NORD_RED}]Error: Ollama is not running. Start it with 'ollama serve'[/{NORD_RED}]")
            return None
        try:
            model_name = console.input(f"[{NORD_BLUE}]Enter local model name: [/{NORD_BLUE}]")
        except (KeyboardInterrupt, EOFError):
            return None
        return f"local:{model_name}"
    else:
        # Try as direct model ID
        try:
            validate_model_id(selection)
            return selection
        except ValueError:
            console.print(f"[{NORD_RED}]Invalid selection[/{NORD_RED}]")
            return None