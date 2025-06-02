import asyncio
import signal
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from .types import Message, Conversation, Agent
from .router import Router
from .transcripts import TranscriptManager
from .checkpoint import ConversationState, CheckpointManager
from .attractors import AttractorManager
from .config_manager import get_config
from .token_management import TokenManager, ConversationTokenPredictor
from .context_manager import ContextWindowManager


class DialogueEngine:
    def __init__(self, router: Router, transcript_manager: TranscriptManager, config: Optional[Dict[str, Any]] = None):
        self.router = router
        self.transcript_manager = transcript_manager
        self.conversation: Optional[Conversation] = None
        self.console = Console()
        
        # Configuration
        self.config = config or get_config()
        
        # Attractor detection
        attractor_config = self.config.get('conversation.attractor_detection', {}) if hasattr(self.config, 'get') else {}
        self.attractor_manager = AttractorManager(attractor_config)
        
        # Checkpoint management
        self.state: Optional[ConversationState] = None
        self.checkpoint_manager = CheckpointManager()
        self.checkpoint_enabled = self.config.get('conversation.checkpoint.enabled', True) if hasattr(self.config, 'get') else True
        self.checkpoint_interval = self.config.get('conversation.checkpoint.auto_save_interval', 10) if hasattr(self.config, 'get') else 10
        
        # Token management
        token_config = self.config.get('token_management', {}) if hasattr(self.config, 'get') else {}
        self.token_management_enabled = token_config.get('enabled', True)
        self.token_warning_threshold = token_config.get('warning_threshold', 10)
        self.token_auto_pause_threshold = token_config.get('auto_pause_threshold', 3)
        self.show_token_metrics = token_config.get('show_metrics', True)
        
        if self.token_management_enabled:
            self.token_manager = TokenManager()
            self.token_predictor = ConversationTokenPredictor(self.token_manager)
        else:
            self.token_manager = None
            self.token_predictor = None
        
        # Context window management
        context_config = self.config.get('context_management', {}) if hasattr(self.config, 'get') else {}
        self.context_management_enabled = context_config.get('enabled', True)
        self.context_warning_threshold = context_config.get('warning_threshold', 80)
        self.context_auto_pause_threshold = context_config.get('auto_pause_threshold', 95)
        self.show_context_usage = context_config.get('show_usage', True)
        
        if self.context_management_enabled:
            self.context_manager = ContextWindowManager()
        else:
            self.context_manager = None
        
        # Signal handling for graceful pause
        self._original_sigint = None
        self._pause_requested = False
    
    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent, 
        initial_prompt: str,
        max_turns: int,
        resume_from_state: Optional[ConversationState] = None,
        show_token_warnings: bool = True
    ):
        # Set up signal handler for graceful pause
        self._setup_signal_handler()
        
        # Initialize or resume conversation
        if resume_from_state:
            self.state = resume_from_state
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt,
                messages=self.state.messages.copy()
            )
            start_turn = self.state.turn_count
            
            # Restore token state if available
            if self.token_management_enabled and self.token_predictor:
                if 'token_history' in self.state.metadata:
                    self.token_predictor.history = self.state.metadata['token_history']
                    self.console.print(f"[dim]Restored token history: {len(self.token_predictor.history)} exchanges[/dim]")
                if 'token_stats' in self.state.metadata:
                    token_stats = self.state.metadata['token_stats']
                    self.console.print(f"[dim]Token usage at pause: "
                                     f"Agent A: {token_stats['agent_a']['percentage']:.1f}%, "
                                     f"Agent B: {token_stats['agent_b']['percentage']:.1f}%[/dim]")
            
            # Restore context state if available
            if self.context_management_enabled and self.context_manager:
                if 'context_stats' in self.state.metadata:
                    context_stats = self.state.metadata['context_stats']
                    self.console.print(f"[dim]Context usage at pause: "
                                     f"Agent A: {context_stats['agent_a']['percentage']:.1f}%, "
                                     f"Agent B: {context_stats['agent_b']['percentage']:.1f}%[/dim]")
            
            self.console.print(f"[green]Resuming conversation from turn {start_turn}[/green]\n")
        else:
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt
            )
            self.state = ConversationState(
                model_a=agent_a.model,
                model_b=agent_b.model,
                agent_a_id=agent_a.id,
                agent_b_id=agent_b.id,
                max_turns=max_turns,
                initial_prompt=initial_prompt,
                transcript_path=str(self.transcript_manager.get_transcript_path())
            )
            start_turn = 0
        
        # Initial message (only if not resuming)
        if not resume_from_state:
            first_message = Message(
                role="user",
                content=initial_prompt,
                agent_id="system"  # System provides initial prompt
            )
            self.conversation.messages.append(first_message)
            self.state.add_message(first_message)
            
            # Display initial prompt
            self.console.print(Panel(
                initial_prompt, 
                title="[bold blue]Initial Prompt[/bold blue]",
                border_style="blue"
            ))
            self.console.print()
            
            # Display initial token budget if enabled
            if self.token_management_enabled and self.token_manager:
                self.console.print("[bold cyan]Token Budget:[/bold cyan]")
                for agent in [agent_a, agent_b]:
                    if agent.model in self.token_manager.limits:
                        limits = self.token_manager.limits[agent.model]
                        self.console.print(f"  • {agent.id} ({agent.model}): "
                                         f"{limits['tpm']:,} tokens/min, {limits['rpm']} requests/min")
                self.console.print()
            
            # Display context window limits if enabled
            if self.context_management_enabled and self.context_manager:
                self.console.print("[bold cyan]Context Windows:[/bold cyan]")
                for agent in [agent_a, agent_b]:
                    if agent.model in self.context_manager.context_limits:
                        limit = self.context_manager.context_limits[agent.model]
                        effective_limit = limit - self.context_manager.reserved_tokens
                        self.console.print(f"  • {agent.id} ({agent.model}): "
                                         f"{effective_limit:,} tokens (total: {limit:,})")
                self.console.print()
        
        # Run conversation loop
        try:
            for turn in range(start_turn, max_turns):
                # Check for pause request
                if self._pause_requested:
                    await self._handle_pause()
                    break
                
                # Check token predictions before proceeding
                if self.token_management_enabled and self.token_predictor and len(self.conversation.messages) > 2:
                    remaining_exchanges = self.token_predictor.predict_remaining_exchanges(
                        agent_a.model, agent_b.model
                    )
                    
                    if remaining_exchanges <= self.token_warning_threshold:
                        growth_pattern = self.token_predictor.get_growth_pattern()
                        self.console.print(
                            f"\n[yellow bold]⚠️  Token Warning: Estimated {remaining_exchanges} exchanges remaining "
                            f"(growth pattern: {growth_pattern})[/yellow bold]\n"
                        )
                        
                        if remaining_exchanges <= self.token_auto_pause_threshold:
                            self.console.print(
                                f"[red bold]🛑 Auto-pausing: Only {remaining_exchanges} exchanges remaining[/red bold]"
                            )
                            self._pause_requested = True
                            continue
                
                # Agent A responds
                response_a = await self._get_agent_response(agent_a.id)
                if response_a is None:  # Rate limit pause requested
                    continue
                self.conversation.messages.append(response_a)
                self.state.add_message(response_a)
                
                # Check context usage for Agent A after adding message
                context_info_a = None
                if self.context_management_enabled and self.context_manager:
                    capacity_a = self.context_manager.get_remaining_capacity(
                        self.conversation.messages, agent_a.model
                    )
                    context_info_a = capacity_a
                    
                    # Check if we should warn about context usage
                    if self.context_manager.should_warn(
                        self.conversation.messages, agent_a.model, self.context_warning_threshold
                    ):
                        turns_remaining = self.context_manager.predict_turns_remaining(
                            self.conversation.messages, agent_a.model
                        )
                        self.console.print(
                            f"\n[yellow bold]⚠️  Context Warning ({agent_a.model}): "
                            f"{capacity_a['percentage']:.1f}% used, ~{turns_remaining} turns remaining[/yellow bold]\n"
                        )
                
                self._display_message(response_a, agent_a.model, context_info=context_info_a)
                
                # Check for auto-pause due to context limits before Agent B
                if self.context_management_enabled and self.context_manager:
                    if self.context_manager.should_pause(
                        self.conversation.messages, agent_a.model, self.context_auto_pause_threshold
                    ):
                        self.console.print(
                            f"[red bold]🛑 Auto-pausing: Context window {capacity_a['percentage']:.1f}% full "
                            f"for {agent_a.model}[/red bold]"
                        )
                        self._pause_requested = True
                        continue
                
                # Agent B responds  
                response_b = await self._get_agent_response(agent_b.id)
                if response_b is None:  # Rate limit pause requested
                    continue
                self.conversation.messages.append(response_b)
                self.state.add_message(response_b)
                
                # Check context usage for Agent B after adding message
                context_info_b = None
                if self.context_management_enabled and self.context_manager:
                    capacity_b = self.context_manager.get_remaining_capacity(
                        self.conversation.messages, agent_b.model
                    )
                    context_info_b = capacity_b
                    
                    # Check if we should warn about context usage
                    if self.context_manager.should_warn(
                        self.conversation.messages, agent_b.model, self.context_warning_threshold
                    ):
                        turns_remaining = self.context_manager.predict_turns_remaining(
                            self.conversation.messages, agent_b.model
                        )
                        self.console.print(
                            f"\n[yellow bold]⚠️  Context Warning ({agent_b.model}): "
                            f"{capacity_b['percentage']:.1f}% used, ~{turns_remaining} turns remaining[/yellow bold]\n"
                        )
                        
                    # Check for auto-pause due to context limits
                    if self.context_manager.should_pause(
                        self.conversation.messages, agent_b.model, self.context_auto_pause_threshold
                    ):
                        self.console.print(
                            f"[red bold]🛑 Auto-pausing: Context window {capacity_b['percentage']:.1f}% full "
                            f"for {agent_b.model}[/red bold]"
                        )
                        self._pause_requested = True
                
                self._display_message(response_b, agent_b.model, context_info=context_info_b)
                
                # Auto-save transcript after each turn
                await self.transcript_manager.save(self.conversation)
                
                # Check for attractor detection
                message_contents = [msg.content for msg in self.conversation.messages if msg.role != "system"]
                
                # Show indicator when checking
                if self.attractor_manager.enabled and (turn + 1) % self.attractor_manager.check_interval == 0:
                    self.console.print("[dim]🔍 Checking for patterns...[/dim]", end='')
                    
                if attractor_result := self.attractor_manager.check(message_contents, turn + 1, show_progress=False):
                    self.console.print(" [red bold]ATTRACTOR FOUND![/red bold]")
                    await self._handle_attractor_detection(attractor_result)
                    if attractor_result['action'] == 'stop':
                        break
                elif self.attractor_manager.enabled and (turn + 1) % self.attractor_manager.check_interval == 0:
                    self.console.print(" [green]continuing normally.[/green]")
                
                # Auto-checkpoint at intervals
                if self.checkpoint_enabled and (turn + 1) % self.checkpoint_interval == 0:
                    # Save token state in metadata if enabled
                    if self.token_management_enabled and self.token_predictor:
                        self.state.metadata['token_history'] = self.token_predictor.history
                        self.state.metadata['token_stats'] = {
                            'agent_a': self.token_manager.get_usage_stats(agent_a.model),
                            'agent_b': self.token_manager.get_usage_stats(agent_b.model)
                        }
                    
                    # Save context state in metadata if enabled
                    if self.context_management_enabled and self.context_manager:
                        self.state.metadata['context_stats'] = {
                            'agent_a': self.context_manager.get_remaining_capacity(
                                self.conversation.messages, agent_a.model
                            ),
                            'agent_b': self.context_manager.get_remaining_capacity(
                                self.conversation.messages, agent_b.model
                            )
                        }
                    
                    checkpoint_path = self.state.save_checkpoint()
                    self.console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
                
                # Show turn counter with detection status, token metrics, and context usage
                detection_status = ""
                if self.attractor_manager.enabled:
                    detection_status = " [🔍 Detection Active]"
                    # Show when we're checking
                    if (turn + 1) % self.attractor_manager.check_interval == 0:
                        detection_status += " - Pattern check performed"
                
                # Add token metrics if enabled
                token_status = ""
                if self.token_management_enabled and self.token_manager:
                    stats_a = self.token_manager.get_usage_stats(agent_a.model)
                    stats_b = self.token_manager.get_usage_stats(agent_b.model)
                    
                    # Show the most constrained model
                    if stats_a['percentage'] > stats_b['percentage']:
                        token_status = f" | Tokens: {stats_a['percentage']:.1f}% used"
                    else:
                        token_status = f" | Tokens: {stats_b['percentage']:.1f}% used"
                    
                    # Add remaining exchanges prediction
                    if self.token_predictor and len(self.conversation.messages) > 2:
                        remaining = self.token_predictor.predict_remaining_exchanges(
                            agent_a.model, agent_b.model
                        )
                        token_status += f" (~{remaining} exchanges left)"
                
                # Add context window status if enabled
                context_status = ""
                if self.context_management_enabled and self.context_manager:
                    # Get context usage for both models
                    capacity_a = self.context_manager.get_remaining_capacity(
                        self.conversation.messages, agent_a.model
                    )
                    capacity_b = self.context_manager.get_remaining_capacity(
                        self.conversation.messages, agent_b.model
                    )
                    
                    # Show the most constrained model's context usage
                    if capacity_a['percentage'] > capacity_b['percentage']:
                        context_status = f" | Context: {capacity_a['percentage']:.1f}% full"
                        # Add turns remaining prediction
                        turns_left = self.context_manager.predict_turns_remaining(
                            self.conversation.messages, agent_a.model
                        )
                        if turns_left < 20:  # Only show if getting low
                            context_status += f" (~{turns_left} turns left)"
                    else:
                        context_status = f" | Context: {capacity_b['percentage']:.1f}% full"
                        # Add turns remaining prediction
                        turns_left = self.context_manager.predict_turns_remaining(
                            self.conversation.messages, agent_b.model
                        )
                        if turns_left < 20:  # Only show if getting low
                            context_status += f" (~{turns_left} turns left)"
                
                self.console.print(f"\n[dim]Turn {turn + 1}/{max_turns} completed{detection_status}{token_status}{context_status}[/dim]\n")
                
        except KeyboardInterrupt:
            # Handled by signal handler
            pass
        finally:
            # Restore original signal handler
            self._restore_signal_handler()
            # Save final transcript
            await self.transcript_manager.save(self.conversation)
    
    def _display_message(self, message: Message, model_name: str, context_info: Optional[Dict[str, Any]] = None):
        """Display a message in the terminal with Rich formatting, token metrics, and context usage."""
        if message.agent_id == "agent_a":
            title = f"[bold green]Agent A ({model_name})[/bold green]"
            border_style = "green"
        else:
            title = f"[bold magenta]Agent B ({model_name})[/bold magenta]"
            border_style = "magenta"
        
        # Add token metrics to title if enabled
        if self.token_management_enabled and self.show_token_metrics and self.token_manager:
            stats = self.token_manager.get_usage_stats(model_name)
            if stats['tokens_limit'] > 0:
                title += f" [dim]({stats['tokens_used']:,}/{stats['tokens_limit']:,} tokens)[/dim]"
        
        # Add context usage to title if enabled and available
        if self.context_management_enabled and self.show_context_usage and context_info:
            usage_str = self.context_manager.format_usage(context_info)
            title += f" [dim]| Context: {usage_str}[/dim]"
        
        self.console.print(Panel(
            message.content,
            title=title,
            border_style=border_style
        ))
        self.console.print()
            
    async def _get_agent_response(self, agent_id: str) -> Message:
        """Get agent response with token management."""
        # Get the target agent
        target_agent = next(a for a in self.conversation.agents if a.id == agent_id)
        
        # Token management checks if enabled
        if self.token_management_enabled and self.token_manager:
            # Count tokens in conversation history
            conversation_tokens = sum(
                self.token_manager.count_tokens(msg.content, target_agent.model)
                for msg in self.conversation.messages
            )
            
            # Estimate tokens for new response (based on recent messages or default)
            if len(self.conversation.messages) >= 2:
                recent_avg = sum(
                    self.token_manager.count_tokens(msg.content, target_agent.model)
                    for msg in self.conversation.messages[-2:]
                ) // 2
                estimated_response_tokens = int(recent_avg * 1.2)  # 20% buffer
            else:
                estimated_response_tokens = 200  # Default estimate
            
            total_estimated = conversation_tokens + estimated_response_tokens
            
            # Check availability
            can_proceed, wait_time = self.token_manager.check_availability(
                target_agent.model, total_estimated
            )
            
            if not can_proceed:
                # Show warning and potentially pause
                self.console.print(f"\n[red bold]⚠️  Rate limit approaching for {target_agent.model}![/red bold]")
                self.console.print(f"[yellow]Need to wait {wait_time} seconds before continuing.[/yellow]")
                
                if wait_time <= self.token_auto_pause_threshold * 60:  # Auto-pause threshold in minutes
                    # Wait with progress indicator
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=self.console
                    ) as progress:
                        task = progress.add_task(f"Waiting {wait_time}s for rate limit...", total=wait_time)
                        for i in range(wait_time):
                            await asyncio.sleep(1)
                            progress.update(task, advance=1, description=f"Waiting {wait_time-i-1}s for rate limit...")
                else:
                    # Too long to wait - pause conversation
                    self.console.print(f"\n[red]Rate limit wait time too long ({wait_time}s). Pausing conversation.[/red]")
                    self._pause_requested = True
                    return None
        
        # Create a message from this agent
        last_message = self.conversation.messages[-1]
        
        # Route through the router
        start_time = time.time()
        response = await self.router.route_message(last_message, self.conversation)
        response_time = time.time() - start_time
        
        # Track token usage if enabled
        if self.token_management_enabled and self.token_manager:
            # Count actual tokens used
            prompt_tokens = sum(
                self.token_manager.count_tokens(msg.content, target_agent.model)
                for msg in self.conversation.messages
            )
            response_tokens = self.token_manager.count_tokens(response.content, target_agent.model)
            
            # Track usage
            self.token_manager.track_usage(target_agent.model, prompt_tokens + response_tokens)
            
            # Update predictor
            if self.token_predictor:
                self.token_predictor.add_exchange(prompt_tokens, response_tokens)
        
        return response
    
    def _setup_signal_handler(self):
        """Set up signal handlers for pause and stop."""
        # Ctrl+Z for pause (SIGTSTP)
        def pause_handler(signum, frame):
            self._pause_requested = True
            self.console.print("\n[yellow]⏸️  Pause requested... Finishing current turn.[/yellow]")
        
        # Ctrl+C for stop (SIGINT)
        def stop_handler(signum, frame):
            self.console.print("\n[red]🛑 Stop requested. Saving transcript...[/red]")
            raise KeyboardInterrupt()
        
        self._original_sigtstp = signal.signal(signal.SIGTSTP, pause_handler)
        self._original_sigint = signal.signal(signal.SIGINT, stop_handler)
        
        # Show controls with token and context management info
        controls_text = "[dim]Controls: [Ctrl+Z] Pause | [Ctrl+C] Stop"
        if self.token_management_enabled:
            controls_text += " | Token management: ON"
        if self.context_management_enabled:
            controls_text += " | Context tracking: ON"
        controls_text += "[/dim]\n"
        self.console.print(controls_text)
    
    def _restore_signal_handler(self):
        """Restore original signal handlers."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)
        if hasattr(self, '_original_sigtstp') and self._original_sigtstp:
            signal.signal(signal.SIGTSTP, self._original_sigtstp)
    
    async def _handle_pause(self):
        """Handle pause request."""
        self.console.print("\n[yellow]Pausing conversation...[/yellow]")
        
        # Save token state in metadata if enabled
        if self.token_management_enabled and self.token_predictor:
            # Get both agents from the conversation
            agent_a = next(a for a in self.conversation.agents if a.id == "agent_a")
            agent_b = next(a for a in self.conversation.agents if a.id == "agent_b")
            
            self.state.metadata['token_history'] = self.token_predictor.history
            self.state.metadata['token_stats'] = {
                'agent_a': self.token_manager.get_usage_stats(agent_a.model),
                'agent_b': self.token_manager.get_usage_stats(agent_b.model)
            }
        
        # Save context window state in metadata if enabled
        if self.context_management_enabled and self.context_manager:
            # Get both agents from the conversation
            agent_a = next(a for a in self.conversation.agents if a.id == "agent_a")
            agent_b = next(a for a in self.conversation.agents if a.id == "agent_b")
            
            self.state.metadata['context_stats'] = {
                'agent_a': self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agent_a.model
                ),
                'agent_b': self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agent_b.model
                )
            }
        
        checkpoint_path = self.state.save_checkpoint()
        self.console.print(f"\n[green]Checkpoint saved: {checkpoint_path}[/green]")
        self.console.print(f"[green]Resume with: pidgin resume {checkpoint_path}[/green]\n")
    
    async def _handle_attractor_detection(self, result: Dict[str, Any]):
        """Handle attractor detection event."""
        # Clear visual separator
        self.console.print(f"\n[red]{'='*60}[/red]")
        self.console.print(f"[red bold]🚨 ATTRACTOR DETECTED - Turn {result['turn_detected']}/{self.state.max_turns}[/red bold]")
        self.console.print(f"[red]{'='*60}[/red]")
        
        # Display detection details in a clear format
        self.console.print(f"[yellow]Type:[/yellow]       {result['type']}")
        self.console.print(f"[yellow]Pattern:[/yellow]    {result['description']}")
        self.console.print(f"[yellow]Confidence:[/yellow] {result['confidence']:.0%}")
        
        # Show pattern details if available
        if 'pattern' in result:
            pattern_str = result['pattern']
            if len(pattern_str) > 50:
                pattern_str = pattern_str[:50] + "..."
            self.console.print(f"[yellow]Structure:[/yellow]  {pattern_str}")
        
        self.console.print(f"[red]{'='*60}[/red]\n")
        
        # Save attractor analysis
        self.console.print("[dim]💾 Saving transcript with detection data...[/dim]")
        if self.state.transcript_path:
            analysis_path = self.attractor_manager.save_analysis(Path(self.state.transcript_path))
            if analysis_path:
                self.console.print(f"[green]✅ Analysis saved to: {analysis_path}[/green]")
        
        # Save the transcript with metadata
        await self.transcript_manager.save(self.conversation)
        self.console.print(f"[green]✅ Transcript saved to: {self.state.transcript_path}[/green]")
        
        if result['action'] == 'stop':
            self.console.print("\n[red bold]Ending conversation - Structural attractor reached[/red bold]\n")
        elif result['action'] == 'pause':
            self._pause_requested = True