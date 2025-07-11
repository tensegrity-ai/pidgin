# pidgin/cli/run.py
"""Unified run command for conversations and experiments."""

import os
import sys
import asyncio
import uuid
import signal
import time
import json
from typing import Optional, List
from pathlib import Path
from datetime import datetime

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .ollama_setup import normalize_local_model_names, ensure_ollama_models_ready
from ..ui.display_utils import DisplayUtils
from ..providers import APIKeyError
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
    NORD_BLUE, NORD_YELLOW, NORD_RED, NORD_GREEN, NORD_CYAN, NORD_DARK,
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
display = DisplayUtils(console)

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
              help='Show formatted event stream during conversation')
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
        quiet, tail, notify, name, max_parallel):
    """Run AI conversations - single or multiple.

    This unified command runs conversations between two AI agents.
    By default shows the conversation messages as they are generated.

    [bold]EXAMPLES:[/bold]

    [#4c566a]Basic conversation: [/#4c566a]
      pidgin run -a claude -b gpt

    [#4c566a]Event stream:       [/#4c566a]
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
    mode_count = sum([quiet, tail])
    if mode_count > 1:
        console.print(f"[{NORD_RED}]Error: Can only use one of --quiet or --tail[/{NORD_RED}]")
        return
    
    if quiet:
        display_mode = "quiet"
        # Quiet mode should run in background and notify
        background = True
        notify = True
    elif tail:
        display_mode = "tail"  # Show formatted event stream
    else:
        display_mode = "verbose"  # Default: show conversation messages
    
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
            console.print()  # Add newline
            display.warning(
                "Model selection cancelled",
                context="Use -a and -b flags to specify models.\nExample: pidgin run -a claude -b gpt",
                use_panel=False
            )
            return
        except Exception as e:
            console.print()  # Add newline
            display.error(
                f"Error during model selection: {e}",
                context="Use -a and -b flags to specify models directly.\nExample: pidgin run -a claude -b gpt",
                use_panel=False
            )
            return
    
    if not agent_b:
        try:
            agent_b = _prompt_for_model("Select second agent (Agent B)")
            if not agent_b:
                return
        except (KeyboardInterrupt, EOFError):
            console.print()  # Add newline
            display.warning(
                "Model selection cancelled",
                context="Use -a and -b flags to specify models.\nExample: pidgin run -a claude -b gpt",
                use_panel=False
            )
            return
        except Exception as e:
            console.print()  # Add newline
            display.error(
                f"Error during model selection: {e}",
                context="Use -a and -b flags to specify models directly.\nExample: pidgin run -a claude -b gpt",
                use_panel=False
            )
            return
    
    # Validate models
    try:
        agent_a_id, agent_a_name = validate_model_id(agent_a)
        agent_b_id, agent_b_name = validate_model_id(agent_b)
    except ValueError as e:
        display.error(str(e), use_panel=False)
        return

    # Handle temperature settings
    temp_a, temp_b = resolve_temperatures(temperature, temp_a, temp_b)
    
    # Parse and validate dimensions
    if dimension:
        dimension = parse_dimensions(list(dimension))
    
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
            display.dim(f"Using default convergence threshold: {convergence_threshold} → {convergence_action}")
    
    # Default convergence action
    if convergence_action is None:
        convergence_action = 'stop'  # Always use 'stop' as default
    
    # Force quiet mode if parallel execution
    if max_parallel > 1 and not quiet:
        quiet = True
        display.warning(
            f"Parallel execution (max_parallel={max_parallel}) requires quiet mode",
            use_panel=False
        )
    
    # Generate fun name if not provided
    if not name:
        name = generate_experiment_name()
        display.dim(f"Generated experiment name: {name}")
    
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
        choose_names, quiet, notify,
        display_mode, first_speaker_id, output
    )



def _run_conversations(agent_a_id, agent_b_id, agent_a_name, agent_b_name,
                      repetitions, max_turns, temp_a, temp_b,
                      initial_prompt, dimensions, name, max_parallel,
                      convergence_threshold, convergence_action,
                      awareness, awareness_a, awareness_b,
                      choose_names, quiet, notify,
                      display_mode, first_speaker_id, output_dir):
    """Run conversations using the unified execution path."""
    # Determine display mode for experiments
    # For parallel execution or quiet mode, don't use interactive displays
    if max_parallel > 1 or quiet:
        experiment_display_mode = 'none'
        if display_mode in ['tail', 'verbose'] and max_parallel > 1:
            display.warning(
                f"--{display_mode} is not supported with parallel execution",
                use_panel=False
            )
    else:
        # Non-quiet mode can use any display mode
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
    config_lines = []
    config_lines.append(f"Name: {name}")
    config_lines.append(f"Models: {format_model_display(agent_a_id)} ↔ {format_model_display(agent_b_id)}")
    config_lines.append(f"Conversations: {repetitions}")
    config_lines.append(f"Turns per conversation: {max_turns}")
    
    if max_parallel > 1:
        config_lines.append(f"Parallel execution: {max_parallel}")
    
    if initial_prompt != "Hello":
        if len(initial_prompt) > 50:
            config_lines.append(f"Initial prompt: {initial_prompt[:50]}...")
        else:
            config_lines.append(f"Initial prompt: {initial_prompt}")
    
    if temp_a is not None or temp_b is not None:
        temp_parts = []
        if temp_a is not None:
            temp_parts.append(f"A: {temp_a}")
        if temp_b is not None:
            temp_parts.append(f"B: {temp_b}")
        config_lines.append(f"Temperature: {', '.join(temp_parts)}")
    
    if convergence_threshold:
        config_lines.append(f"Convergence: {convergence_threshold} → {convergence_action}")
    
    display.info("\n".join(config_lines), title="◆ Experiment Configuration", use_panel=True)
    
    # Check if experiment already exists
    from ..io.jsonl_reader import JSONLExperimentReader
    jsonl_reader = JSONLExperimentReader(get_experiments_dir())
    experiments = jsonl_reader.list_experiments()
    existing = next((exp for exp in experiments if exp.get('name') == name), None)

    if existing:
        display.error(
            f"Experiment session '{name}' already exists",
            context=f"Use 'pidgin attach {name}' to monitor",
            use_panel=False
        )
        return
    
    # Validate configuration
    errors = config.validate()
    if errors:
        error_msg = "Configuration errors:\n\n"
        for error in errors:
            error_msg += f"  • {error}\n"
        display.error(error_msg.rstrip(), use_panel=True)
        return
    
    # Always run via daemon
    base_dir = get_experiments_dir()
    manager = ExperimentManager(base_dir=base_dir)
    
    try:
        # Always start via manager (creates daemon + PID file)
        exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
        
        # Show start message
        console.print(f"\n[#a3be8c]✓ Started: {exp_id}[/#a3be8c]")
        
        if quiet:
            # Quiet mode: just show commands and exit
            console.print(f"\n[#4c566a]Running in background. Check progress:[/#4c566a]")
            cmd_lines = []
            cmd_lines.append(f"pidgin monitor              # Monitor all experiments")
            cmd_lines.append(f"pidgin stop {name}    # Stop by name")
            cmd_lines.append(f"pidgin stop {exp_id[:8]}  # Stop by ID")
            cmd_lines.append(f"tail -f {get_experiments_dir()}/{exp_id}/*.jsonl")
            display.info("\n".join(cmd_lines), title="Commands", use_panel=True)
        else:
            # Non-quiet mode: show live display
            console.print(f"[{NORD_DARK}]Ctrl+C to exit display • experiment continues[/{NORD_DARK}]")
            console.print()
            
            # Import the display runners
            from ..experiments.display_runner import run_display
            
            try:
                # Run the display (this will tail JSONL files and show live updates)
                asyncio.run(run_display(exp_id, display_mode))
                
                # After display exits, show completion info
                exp_dir = get_experiments_dir() / exp_id
                manifest_path = exp_dir / "manifest.json"
                
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        
                        # Extract statistics from manifest
                        completed = manifest.get("completed_conversations", 0)
                        failed = manifest.get("failed_conversations", 0)
                        total = manifest.get("total_conversations", repetitions)
                        status = manifest.get("status", "completed")
                        
                        # Calculate duration
                        start_time = manifest.get("started_at")
                        end_time = manifest.get("completed_at")
                        if start_time and end_time:
                            from datetime import datetime
                            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            duration = (end_dt - start_dt).total_seconds()
                        else:
                            duration = 0
                        
                        # Display completion info
                        display.experiment_complete(
                            name=name,
                            experiment_id=exp_id,
                            completed=completed,
                            failed=failed,
                            total=total,
                            duration_seconds=duration,
                            status=status,
                            experiment_dir=str(exp_dir)
                        )
                        
                        if notify and status == "completed":
                            send_notification(
                                title="Pidgin Experiment Complete",
                                message=f"Experiment '{name}' has finished ({completed}/{total} conversations)"
                            )
                        else:
                            # Terminal bell notification
                            print('\a', end='', flush=True)
                    except Exception:
                        # If can't read manifest, just note that display exited
                        display.info("Display exited. Experiment continues running in background.", use_panel=False)
                else:
                    display.info("Display exited. Experiment continues running in background.", use_panel=False)
                    
            except KeyboardInterrupt:
                # Ctrl+C just exits display, not the experiment
                console.print()
                display.info("Display exited. Experiment continues running in background.", use_panel=False)
                console.print(f"\n[#4c566a]Check progress with:[/#4c566a]")
                console.print(f"  pidgin monitor")
                console.print(f"  pidgin stop {name}")
                
    except Exception as e:
        display.error(f"Failed to start experiment: {str(e)}", use_panel=True)
        raise


def _prompt_for_model(prompt_text: str) -> Optional[str]:
    """Interactive model selection."""
    display.info(prompt_text, use_panel=False)
    
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
            
        # Show provider section
        display.dim(f"\n{provider.title()}:")
        
        for model_id, config in providers[provider]:
            glyph = MODEL_EMOJIS.get(model_id, "●")
            display.dim(f"  {idx}. {glyph} {config.shortname}")
            model_map[str(idx)] = model_id
            idx += 1
    
    # Add option for custom local model
    display.dim("\nOther:")
    display.dim(f"  {idx}. ▸ Custom local model (requires Ollama)")
    
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
            display.error("Ollama is not running. Start it with 'ollama serve'", use_panel=False)
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
            display.error("Invalid selection", use_panel=False)
            return None