"""Event-sourced dialogue engine for Pidgin."""

import time
import uuid
import traceback
from typing import Optional, List, Tuple

from rich.console import Console
from rich.panel import Panel

from .types import Agent, Message, ConversationTurn
from .router import Router
from .events import EventStore, Event, EventType, create_event
from .conductor import Conductor
from .convergence import ConvergenceCalculator
from .attractors import AttractorManager
from .context_manager import ContextWindowManager
from .utils.terminal import check_for_spacebar


class EventDialogueEngine:
    """Dialogue engine that emits events as the source of truth."""
    
    def __init__(self, 
                 router: Router, 
                 event_store: EventStore,
                 config: dict):
        self.router = router
        self.events = event_store
        self.config = config
        self.console = Console()
        
        # Core components
        self.convergence_calculator = ConvergenceCalculator()
        self.attractor_manager = AttractorManager(
            config.get('conversation', {}).get('attractor_detection', {})
        )
        
        # Context management
        context_config = config.get('context_management', {})
        self.context_management_enabled = context_config.get('enabled', True)
        if self.context_management_enabled:
            self.context_manager = ContextWindowManager()
        else:
            self.context_manager = None
            
        # Conversation state (rebuilt from events if resuming)
        self.messages: List[Message] = []
        self.experiment_id: Optional[str] = None
        self.conductor: Optional[Conductor] = None
        
    async def run_conversation(self, 
                             agent_a: Agent, 
                             agent_b: Agent,
                             initial_prompt: str, 
                             max_turns: int,
                             manual_mode: bool = False,
                             experiment_id: Optional[str] = None) -> str:
        """Run a conversation, emitting events throughout."""
        
        # Generate or use provided experiment ID
        self.experiment_id = experiment_id or uuid.uuid4().hex[:8]
        
        # Initialize conductor
        if manual_mode:
            self.conductor = Conductor(self.console, mode="manual")
            self.console.print("[bold cyan]🎼 Manual Mode Active[/bold cyan]")
            self.console.print("[dim]You will approve each message before it's sent.[/dim]\n")
        else:
            self.conductor = Conductor(self.console, mode="flowing")
            self.console.print("[bold cyan]🎼 Flowing Mode (Default)[/bold cyan]")
            self.console.print("[dim]Conversation flows automatically. Press Spacebar to interrupt.[/dim]\n")
        
        try:
            # Emit start event
            self.events.append(create_event(
                EventType.EXPERIMENT_STARTED,
                self.experiment_id,
                data={
                    'model_a': agent_a.model,
                    'model_b': agent_b.model,
                    'initial_prompt': initial_prompt,
                    'max_turns': max_turns,
                    'manual_mode': manual_mode,
                    'config': self.config
                }
            ))
            
            # Display initial prompt
            self.console.print(
                Panel(
                    initial_prompt,
                    title="[bold blue]Initial Prompt[/bold blue]",
                    border_style="blue",
                )
            )
            self.console.print()
            
            # Add initial prompt to messages
            self.messages.append(Message(
                role="user",
                content=initial_prompt,
                agent_id="system"
            ))
            
            # Display context windows if enabled
            if self.context_management_enabled and self.context_manager:
                self._display_context_limits(agent_a, agent_b)
            
            # Main conversation loop
            for turn in range(max_turns):
                should_break = await self._run_turn(turn, agent_a, agent_b, max_turns)
                if should_break:
                    break
            
            # Emit completion event
            self.events.append(create_event(
                EventType.EXPERIMENT_COMPLETED,
                self.experiment_id,
                turn_number=turn,
                data={
                    'final_turn': turn,
                    'status': 'completed',
                    'total_messages': len(self.messages)
                }
            ))
            
            return self.experiment_id
            
        except Exception as e:
            # Emit failure event
            self.events.append(create_event(
                EventType.EXPERIMENT_FAILED,
                self.experiment_id,
                turn_number=turn if 'turn' in locals() else None,
                data={
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
            ))
            raise
    
    async def _run_turn(self, turn: int, agent_a: Agent, agent_b: Agent, max_turns: int) -> bool:
        """Run a single conversation turn. Returns True if should break loop."""
        
        # Emit turn started
        self.events.append(create_event(
            EventType.TURN_STARTED,
            self.experiment_id,
            turn_number=turn
        ))
        
        # Check context limits before starting
        if self.context_management_enabled and self.context_manager:
            if self._check_context_limits(agent_a, agent_b, turn):
                return True  # Auto-paused due to context
        
        # Agent A response
        response_a, interrupted_a = await self._get_streaming_response(turn, agent_a)
        if response_a:
            self.messages.append(response_a)
            
            # Check if conductor intervention needed after interruption
            if interrupted_a and self.conductor:
                self.conductor.is_paused = True
        
        # Skip Agent B if A was interrupted
        if interrupted_a:
            self.events.append(create_event(
                EventType.TURN_COMPLETED,
                self.experiment_id,
                turn_number=turn,
                data={'partial_turn': True, 'interrupted_agent': 'agent_a'}
            ))
        else:
            # Agent B response
            response_b, interrupted_b = await self._get_streaming_response(turn, agent_b)
            if response_b:
                self.messages.append(response_b)
                
                # Check if conductor intervention needed after interruption
                if interrupted_b and self.conductor:
                    self.conductor.is_paused = True
            
            # End-of-turn conductor intervention (only if not interrupted)
            if not interrupted_b and self.conductor:
                current_turn = ConversationTurn(
                    agent_a_message=response_a,
                    agent_b_message=response_b,
                    turn_number=turn + 1
                )
                
                intervention = self.conductor.get_intervention(current_turn)
                if intervention:
                    self.messages.append(intervention)
                    self.events.append(create_event(
                        EventType.CONDUCTOR_INTERVENTION,
                        self.experiment_id,
                        turn_number=turn,
                        data={
                            'source': intervention.agent_id,
                            'content': intervention.content
                        }
                    ))
            
            # Calculate convergence after both responses
            if response_a and response_b:
                convergence = self.convergence_calculator.calculate(self.messages)
                self.events.append(create_event(
                    EventType.CONVERGENCE_MEASURED,
                    self.experiment_id,
                    turn_number=turn,
                    data={'score': convergence}
                ))
                
                # Auto-pause at high convergence
                if convergence >= 0.90:
                    self.console.print(
                        f"\n[red bold]⚠️  AUTO-PAUSE: Convergence reached {convergence:.2f}[/red bold]"
                    )
                    self.events.append(create_event(
                        EventType.PAUSE_REQUESTED,
                        self.experiment_id,
                        turn_number=turn,
                        data={'reason': 'high_convergence', 'score': convergence}
                    ))
                    return True
            
            # Check for attractors
            if self.attractor_manager.enabled and (turn + 1) % self.attractor_manager.check_interval == 0:
                message_contents = [msg.content for msg in self.messages if msg.role != "system"]
                
                self.console.print("[dim]🔍 Checking for patterns...[/dim]", end="")
                
                if attractor_result := self.attractor_manager.check(message_contents, turn + 1, show_progress=False):
                    self.console.print(" [red bold]ATTRACTOR FOUND![/red bold]")
                    
                    self.events.append(create_event(
                        EventType.ATTRACTOR_DETECTED,
                        self.experiment_id,
                        turn_number=turn,
                        data=attractor_result
                    ))
                    
                    self._display_attractor(attractor_result)
                    
                    if attractor_result["action"] == "stop":
                        return True
                else:
                    self.console.print(" [green]continuing normally.[/green]")
            
            # Emit turn completed
            self.events.append(create_event(
                EventType.TURN_COMPLETED,
                self.experiment_id,
                turn_number=turn,
                data={'convergence': convergence if 'convergence' in locals() else None}
            ))
        
        # Display turn counter
        self._display_turn_status(turn + 1, max_turns)
        
        return False
    
    async def _get_streaming_response(self, turn: int, agent: Agent) -> Tuple[Optional[Message], bool]:
        """Get response with streaming and interrupt capability."""
        
        # Emit response started
        self.events.append(create_event(
            EventType.RESPONSE_STARTED,
            self.experiment_id,
            turn_number=turn,
            agent_id=agent.id,
            data={'model': agent.model}
        ))
        
        chunks = []
        interrupted = False
        start_time = time.time()
        
        try:
            # Show streaming status
            self.console.print("", end="\r")
            
            last_check = time.time()
            chunk_count = 0
            
            async for chunk, _ in self.router.get_next_response_stream(self.messages, agent.id):
                chunks.append(chunk)
                chunk_count += 1
                
                # Update status line
                char_count = len(''.join(chunks))
                self.console.print(
                    f"\r[dim]Streaming... {char_count} chars | "
                    f"[yellow]Press SPACE to interrupt[/yellow]",
                    end="",
                    highlight=False
                )
                
                # Emit streaming progress periodically
                if chunk_count % 10 == 0:
                    self.events.append(create_event(
                        EventType.STREAM_CHUNK_RECEIVED,
                        self.experiment_id,
                        turn_number=turn,
                        agent_id=agent.id,
                        data={
                            'chunk_count': chunk_count,
                            'total_chars': char_count
                        }
                    ))
                
                # Check for interrupt every 100ms
                if time.time() - last_check > 0.1:
                    if check_for_spacebar():
                        interrupted = True
                        print('\a', end='', flush=True)  # System bell
                        break
                    last_check = time.time()
                    
        except Exception as e:
            # Clear status line
            self.console.print("\r" + " " * 60 + "\r", end="")
            
            # Emit API failure
            self.events.append(create_event(
                EventType.API_CALL_FAILED,
                self.experiment_id,
                turn_number=turn,
                agent_id=agent.id,
                data={
                    'error': str(e),
                    'provider': agent.model.split('-')[0]
                }
            ))
            
            # Check for rate limit
            if "rate limit" in str(e).lower():
                self.console.print(f"\n[red bold]⚠️  Hit rate limit: {e}[/red bold]")
                self.events.append(create_event(
                    EventType.RATE_LIMIT_WARNING,
                    self.experiment_id,
                    turn_number=turn,
                    agent_id=agent.id,
                    data={'message': str(e)}
                ))
            
            raise
        
        # Clear status line
        self.console.print("\r" + " " * 60 + "\r", end="")
        
        content = ''.join(chunks)
        if not content:
            return None, interrupted
        
        # Estimate tokens (rough approximation)
        tokens = len(content.split()) * 1.3
        
        # Create message
        message = Message(
            role="assistant",
            content=content,
            agent_id=agent.id
        )
        
        # Emit completion or interruption
        if interrupted:
            self.events.append(create_event(
                EventType.RESPONSE_INTERRUPTED,
                self.experiment_id,
                turn_number=turn,
                agent_id=agent.id,
                data={
                    'content': content,  # Include partial content
                    'chars_received': len(content),
                    'duration': time.time() - start_time
                }
            ))
            
            self.console.print("\n[yellow]⚡ Response interrupted![/yellow]")
        else:
            self.events.append(create_event(
                EventType.RESPONSE_COMPLETED,
                self.experiment_id,
                turn_number=turn,
                agent_id=agent.id,
                data={
                    'content': content,
                    'length': len(content),
                    'duration': time.time() - start_time,
                    'tokens': int(tokens),
                    'model': agent.model
                }
            ))
        
        # Display the message
        self._display_message(message, agent.model)
        
        return message, interrupted
    
    def _display_message(self, message: Message, model_name: str):
        """Display a message in the terminal."""
        if message.agent_id == "agent_a":
            title = f"[bold green]Agent A ({model_name})[/bold green]"
            border_style = "green"
        elif message.agent_id == "agent_b":
            title = f"[bold magenta]Agent B ({model_name})[/bold magenta]"
            border_style = "magenta"
        else:
            # System/intervention messages
            title = f"[bold yellow]{message.agent_id.title()}[/bold yellow]"
            border_style = "yellow"
        
        self.console.print(
            Panel(message.content, title=title, border_style=border_style)
        )
        self.console.print()
    
    def _display_context_limits(self, agent_a: Agent, agent_b: Agent):
        """Display context window information."""
        self.console.print("[bold cyan]Context Windows:[/bold cyan]")
        for agent in [agent_a, agent_b]:
            if agent.model in self.context_manager.context_limits:
                limit = self.context_manager.context_limits[agent.model]
                effective_limit = limit - self.context_manager.reserved_tokens
                self.console.print(
                    f"  • {agent.id} ({agent.model}): "
                    f"{effective_limit:,} tokens (total: {limit:,})"
                )
        self.console.print()
    
    def _check_context_limits(self, agent_a: Agent, agent_b: Agent, turn: int) -> bool:
        """Check context limits and emit events. Returns True if should pause."""
        messages_dict = [{"content": msg.content} for msg in self.messages]
        
        capacity_a = self.context_manager.get_remaining_capacity(messages_dict, agent_a.model)
        capacity_b = self.context_manager.get_remaining_capacity(messages_dict, agent_b.model)
        
        # Emit context usage events
        for agent, capacity in [(agent_a, capacity_a), (agent_b, capacity_b)]:
            self.events.append(create_event(
                EventType.CONTEXT_USAGE,
                self.experiment_id,
                turn_number=turn,
                agent_id=agent.id,
                data={
                    'percentage': capacity['percentage'],
                    'tokens_used': capacity['used'],
                    'tokens_remaining': capacity['remaining'],
                    'model': agent.model
                }
            ))
        
        # Check if we should pause
        max_usage = max(capacity_a['percentage'], capacity_b['percentage'])
        if max_usage >= 95:  # Auto-pause threshold
            self.console.print(
                f"[red bold]🛑 Auto-pausing: Context window {max_usage:.1f}% full[/red bold]"
            )
            self.events.append(create_event(
                EventType.PAUSE_REQUESTED,
                self.experiment_id,
                turn_number=turn,
                data={'reason': 'context_limit', 'usage': max_usage}
            ))
            return True
        elif max_usage >= 80:  # Warning threshold
            self.console.print(
                f"\n[yellow bold]⚠️  Context Warning: {max_usage:.1f}% of context window used[/yellow bold]\n"
            )
        
        return False
    
    def _display_attractor(self, result: dict):
        """Display attractor detection results."""
        self.console.print()
        self.console.print(
            f"[red bold]🎯 ATTRACTOR DETECTED - Turn {result['turn_detected']}[/red bold]"
        )
        self.console.print(f"[yellow]Type:[/yellow] {result['type']}")
        self.console.print(f"[yellow]Pattern:[/yellow] {result['description']}")
        self.console.print(f"[yellow]Confidence:[/yellow] {result['confidence']:.0%}")
        if "typical_turns" in result:
            self.console.print(
                f"[yellow]Typical occurrence:[/yellow] Turn {result['typical_turns']}"
            )
        self.console.print()
    
    def _display_turn_status(self, current_turn: int, max_turns: int):
        """Display turn counter with status information."""
        status_parts = [f"Turn {current_turn}/{max_turns}"]
        
        # Add convergence if available
        recent_convergence = [e for e in self.events.subscribers if e.type == EventType.CONVERGENCE_MEASURED]
        if recent_convergence:
            latest = recent_convergence[-1]
            score = latest.data.get('score', 0)
            if score > 0:
                emoji = " ⚠️" if score >= 0.75 else ""
                status_parts.append(f"Conv: {score:.2f}{emoji}")
        
        # Add conductor status
        if self.conductor:
            if self.conductor.mode == "flowing":
                if not self.conductor.is_paused:
                    status_parts.append("[green]Press Spacebar to interrupt[/green]")
                else:
                    status_parts.append("[yellow]PAUSED - interventions enabled[/yellow]")
        
        self.console.print(f"\n[dim]{' | '.join(status_parts)}[/dim]\n")