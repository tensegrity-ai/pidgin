import asyncio
import signal
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from .types import Message, Conversation, Agent, MessageSource
from .router import Router
from .transcripts import TranscriptManager
from .checkpoint import ConversationState, CheckpointManager
from .attractors import AttractorManager
from .config_manager import get_config
from .context_manager import ContextWindowManager
from .conductor import ConductorMiddleware


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
        
        # Store attractor detection result for final summary
        self.attractor_detected = None
    
    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent, 
        initial_prompt: str,
        max_turns: int,
        resume_from_state: Optional[ConversationState] = None,
        show_token_warnings: bool = True,
        conductor_mode: bool = False
    ):
        # Set up signal handler for graceful pause
        self._setup_signal_handler()
        
        # Initialize conductor if requested
        self.conductor = None
        if conductor_mode:
            self.conductor = ConductorMiddleware(self.console)
            self.console.print("[bold cyan]🎼 Conductor Mode Active[/bold cyan]")
            self.console.print("[dim]You will approve each message before it's sent.[/dim]\n")
        
        # Initialize or resume conversation
        if resume_from_state:
            self.state = resume_from_state
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt,
                messages=self.state.messages.copy()
            )
            start_turn = self.state.turn_count
            
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
                
                # PRIORITY 1: Check context window limits (what actually matters)
                context_should_pause = False
                if self.context_management_enabled and self.context_manager and len(self.conversation.messages) > 2:
                    # Check both models for context usage
                    messages_dict = [{'content': msg.content} for msg in self.conversation.messages]
                    
                    capacity_a = self.context_manager.get_remaining_capacity(messages_dict, agent_a.model)
                    capacity_b = self.context_manager.get_remaining_capacity(messages_dict, agent_b.model)
                    
                    # Use the most constrained model
                    max_usage = max(capacity_a['percentage'], capacity_b['percentage'])
                    most_constrained = agent_a.model if capacity_a['percentage'] >= capacity_b['percentage'] else agent_b.model
                    
                    if max_usage >= self.context_warning_threshold:
                        turns_remaining = self.context_manager.predict_turns_remaining(messages_dict, most_constrained)
                        self.console.print(
                            f"\n[yellow bold]⚠️  Context Warning: {max_usage:.1f}% of context window used "
                            f"(~{turns_remaining} turns remaining)[/yellow bold]\n"
                        )
                        
                        if max_usage >= self.context_auto_pause_threshold:
                            self.console.print(
                                f"[red bold]🛑 Auto-pausing: Context window {max_usage:.1f}% full[/red bold]"
                            )
                            context_should_pause = True
                
                if context_should_pause:
                    self._pause_requested = True
                    continue
                
                # Agent A responds
                response_a = await self._get_agent_response(agent_a.id)
                if response_a is None:  # Rate limit pause requested
                    continue
                
                # Conductor intervention if enabled
                if self.conductor:
                    response_a = await self.conductor.process_message(
                        response_a, 
                        f"Agent A ({agent_a.model})",
                        agent_b.id,
                        turn + 1
                    )
                    if response_a is None:  # Message was skipped
                        continue
                
                # Handle system/mediator messages differently
                if self._is_system_message(response_a):
                    # System messages are added to conversation for both agents to see
                    self.conversation.messages.append(response_a)
                    self.state.add_message(response_a)
                    # Display the system message
                    self._display_message(response_a, "", context_info=None)
                    # Continue to next iteration - don't proceed with normal agent flow
                    continue
                else:
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
                
                # Conductor intervention if enabled
                if self.conductor:
                    response_b = await self.conductor.process_message(
                        response_b,
                        f"Agent B ({agent_b.model})",
                        agent_a.id,
                        turn + 1
                    )
                    if response_b is None:  # Message was skipped
                        continue
                
                # Handle system/mediator messages differently
                if self._is_system_message(response_b):
                    # System messages are added to conversation for both agents to see
                    self.conversation.messages.append(response_b)
                    self.state.add_message(response_b)
                    # Display the system message
                    self._display_message(response_b, "", context_info=None)
                    # Continue to next iteration - don't proceed with normal agent flow
                    continue
                else:
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
                
                # Show simplified turn counter
                context_info = ""
                if self.context_management_enabled and self.context_manager:
                    # Get context usage for both models
                    messages_dict = [{'content': msg.content} for msg in self.conversation.messages]
                    capacity_a = self.context_manager.get_remaining_capacity(messages_dict, agent_a.model)
                    capacity_b = self.context_manager.get_remaining_capacity(messages_dict, agent_b.model)
                    
                    # Show the most constrained model's context usage
                    max_usage = max(capacity_a['percentage'], capacity_b['percentage'])
                    max_tokens = capacity_a['used'] if capacity_a['percentage'] > capacity_b['percentage'] else capacity_b['used']
                    
                    context_info = f" | Context: {max_usage:.1f}% ({max_tokens:,} tokens)"
                
                self.console.print(f"\n[dim]Turn {turn + 1}/{max_turns}{context_info}[/dim]\n")
                
        except KeyboardInterrupt:
            # Handled by signal handler
            pass
        finally:
            # Restore original signal handler
            self._restore_signal_handler()
            
            # Save conductor intervention data if available
            if self.conductor:
                intervention_summary = self.conductor.get_intervention_summary()
                if intervention_summary['total_interventions'] > 0:
                    self.state.metadata['conductor_interventions'] = intervention_summary
                    self.console.print(f"\n[dim]Conductor interventions: "
                                     f"{intervention_summary['edits']} edits, "
                                     f"{intervention_summary['injections']} injections, "
                                     f"{intervention_summary['skips']} skips[/dim]")
            
            # Save final transcript
            await self.transcript_manager.save(self.conversation)
    
    def _display_message(self, message: Message, model_name: str, context_info: Optional[Dict[str, Any]] = None):
        """Display a message in the terminal with Rich formatting, token metrics, and context usage."""
        # Determine title and border style based on message source
        if self._is_system_message(message):
            # System/Human/Mediator messages
            display_source = message.display_source
            if message.agent_id == "system":
                title = f"[bold yellow]{display_source}[/bold yellow]"
                border_style = "yellow"
            elif message.agent_id == "human":
                title = f"[bold blue]{display_source}[/bold blue]"
                border_style = "blue"
            elif message.agent_id == "mediator":
                title = f"[bold cyan]{display_source}[/bold cyan]"
                border_style = "cyan"
            else:
                title = f"[bold white]{display_source}[/bold white]"
                border_style = "white"
        else:
            # Agent messages
            if message.agent_id == "agent_a":
                title = f"[bold green]Agent A ({model_name})[/bold green]"
                border_style = "green"
            else:
                title = f"[bold magenta]Agent B ({model_name})[/bold magenta]"
                border_style = "magenta"
        
        # Add context usage to title if enabled and available (only for agent messages)
        if not self._is_system_message(message) and self.context_management_enabled and self.show_context_usage and context_info:
            usage_str = self.context_manager.format_usage(context_info)
            title += f" [dim]| Context: {usage_str}[/dim]"
        
        self.console.print(Panel(
            message.content,
            title=title,
            border_style=border_style
        ))
        self.console.print()
            
    async def _get_agent_response(self, agent_id: str) -> Message:
        """Get agent response."""
        # Get the target agent
        target_agent = next(a for a in self.conversation.agents if a.id == agent_id)
        
        # Create a message from this agent
        last_message = self.conversation.messages[-1]
        
        # Route through the router
        try:
            response = await self.router.route_message(last_message, self.conversation)
            return response
        except Exception as e:
            # Check if it's a rate limit error
            if "rate limit" in str(e).lower():
                self.console.print(f"\n[red bold]⚠️  Hit actual rate limit: {e}[/red bold]")
                self.console.print("[yellow]Saving checkpoint and pausing...[/yellow]")
                await self._handle_pause()
                self.console.print(f"[green]Resume with: pidgin resume --latest[/green]")
                raise SystemExit(0)  # Graceful exit
            else:
                # Other API errors
                self.console.print(f"\n[red]❌ API Error: {e}[/red]")
                await self._handle_pause()
                raise
    
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
        
        # Show controls with context management info
        controls_text = "[dim]Controls: [Ctrl+Z] Pause | [Ctrl+C] Stop"
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
        
        # Save conductor intervention data if available
        if hasattr(self, 'conductor') and self.conductor:
            intervention_summary = self.conductor.get_intervention_summary()
            if intervention_summary['total_interventions'] > 0:
                self.state.metadata['conductor_interventions'] = intervention_summary
        
        checkpoint_path = self.state.save_checkpoint()
        self.console.print(f"\n[green]Checkpoint saved: {checkpoint_path}[/green]")
        self.console.print(f"[green]Resume with: pidgin resume {checkpoint_path}[/green]\n")
    
    def _is_system_message(self, message: Message) -> bool:
        """Check if a message is from system, human, or mediator (non-agent sources)."""
        if hasattr(message, 'source') and message.source:
            return message.source in [MessageSource.SYSTEM, MessageSource.HUMAN, MessageSource.MEDIATOR]
        # Fallback to agent_id check for backward compatibility
        return message.agent_id in ["system", "human", "mediator"]
    
    async def _handle_attractor_detection(self, result: Dict[str, Any]):
        """Handle attractor detection event."""
        # Store for final summary
        self.attractor_detected = result
        
        # Clean, simplified output
        self.console.print()
        self.console.print(f"[red bold]🎯 ATTRACTOR DETECTED - Turn {result['turn_detected']}/{self.state.max_turns}[/red bold]")
        self.console.print(f"[yellow]Type:[/yellow] {result['type']}")
        self.console.print(f"[yellow]Pattern:[/yellow] {result['description']}")
        self.console.print(f"[yellow]Confidence:[/yellow] {result['confidence']:.0%}")
        if 'typical_turns' in result:
            self.console.print(f"[yellow]Typical occurrence:[/yellow] Turn {result['typical_turns']}")
        self.console.print()
        
        # Save attractor analysis
        self.console.print("[dim]💾 Saving transcript with detection data...[/dim]")
        if self.state.transcript_path:
            analysis_path = self.attractor_manager.save_analysis(Path(self.state.transcript_path))
            if analysis_path:
                self.console.print(f"[green]✅ Analysis saved to: {analysis_path}[/green]")
        
        # Save the transcript with metadata
        await self.transcript_manager.save(self.conversation)
        self.console.print(f"[green]✅ Transcript saved to: {self.state.transcript_path}[/green]")
        
        # Show conversation analysis
        self.console.print("\n[cyan]📊 Conversation Analysis:[/cyan]")
        self.console.print(f"• Turns before attractor: {result['turn_detected']}")
        self.console.print(f"• Attractor type: {result['type']}")
        self.console.print(f"• Trigger: Deep conversation → {result['type'].lower()}")
        if 'typical_turns' in result:
            self.console.print(f"• Notable: Detected at turn {result['turn_detected']} (typical: {result['typical_turns']})")
        self.console.print()
        
        if result['action'] == 'stop':
            self.console.print("[red bold]Ending conversation - Structural attractor reached[/red bold]\n")
        elif result['action'] == 'pause':
            self._pause_requested = True