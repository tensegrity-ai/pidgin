import signal
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel

from .attractors import AttractorManager
from .checkpoint import CheckpointManager, ConversationState
from .conductor import Conductor
from .config_manager import get_config
from .context_manager import ContextWindowManager
from .convergence import ConvergenceCalculator
from .metrics import calculate_turn_metrics, update_phase_detection
from .router import Router
from .transcripts import TranscriptManager
from .types import (
    Agent,
    Conversation,
    ConversationTurn,
    Message,
    MessageSource,
)


class DialogueEngine:
    def __init__(
        self,
        router: Router,
        transcript_manager: TranscriptManager,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.router = router
        self.transcript_manager = transcript_manager
        self.conversation: Optional[Conversation] = None
        self.console = Console()

        # Configuration
        self.config = config or get_config()

        # Attractor detection
        attractor_config = (
            self.config.get("conversation.attractor_detection", {})
            if hasattr(self.config, "get")
            else {}
        )
        self.attractor_manager = AttractorManager(attractor_config)

        # Checkpoint management
        self.state: Optional[ConversationState] = None
        self.checkpoint_manager = CheckpointManager()
        self.checkpoint_enabled = (
            self.config.get("conversation.checkpoint.enabled", True)
            if hasattr(self.config, "get")
            else True
        )
        self.checkpoint_interval = (
            self.config.get(
                "conversation.checkpoint.auto_save_interval", 10
            )
            if hasattr(self.config, "get")
            else 10
        )

        # Context window management
        context_config = (
            self.config.get("context_management", {})
            if hasattr(self.config, "get")
            else {}
        )
        self.context_management_enabled = context_config.get(
            "enabled", True
        )
        self.context_warning_threshold = context_config.get(
            "warning_threshold", 80
        )
        self.context_auto_pause_threshold = context_config.get(
            "auto_pause_threshold", 95
        )
        self.show_context_usage = context_config.get(
            "show_usage", True
        )

        if self.context_management_enabled:
            self.context_manager: Optional[
                ContextWindowManager
            ] = ContextWindowManager()
        else:
            self.context_manager = None

        # Signal handling for graceful pause
        self._original_sigint = None
        self._pause_requested = False

        # Store attractor detection result for final summary
        self.attractor_detected: Optional[Dict[str, Any]] = None

        # Convergence tracking
        self.convergence_calculator = ConvergenceCalculator()
        self.convergence_threshold = 0.75  # Default threshold
        self.current_convergence = 0.0
        self.convergence_history: List[Dict[str, Any]] = []
        self.auto_paused_at_convergence = False

        # Enhanced metrics tracking
        self.turn_metrics: Dict[str, List[Any]] = {
            "message_lengths": [],
            "sentence_counts": [],
            "word_diversity": [],
            "emoji_density": [],
            "response_times": [],
        }
        self.phase_detection: Dict[str, Optional[int]] = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }

    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int,
        resume_from_state: Optional[ConversationState] = None,
        show_token_warnings: bool = True,
        manual_mode: bool = False,
        convergence_threshold: float = 0.75,
    ):
        # Set up signal handler for graceful pause
        self._setup_signal_handler()

        # Set convergence threshold
        self.convergence_threshold = convergence_threshold

        # Initialize conductor (default is flowing, manual is optional)
        if manual_mode:
            self.conductor = Conductor(self.console, mode="manual")
            self.console.print(
                "[bold cyan]🎼 Manual Mode Active[/bold cyan]"
            )
            self.console.print(
                "[dim]You will approve each message before it's sent.[/dim]\n"
            )
        else:
            # Default: flowing conductor mode
            self.conductor = Conductor(self.console, mode="flowing")
            self.console.print(
                "[bold cyan]🎼 Flowing Mode (Default)[/bold cyan]"
            )
            self.console.print(
                "[dim]Conversation flows automatically. Press Ctrl+C to pause.[/dim]\n"
            )

        # Initialize or resume conversation
        if resume_from_state:
            self.state = resume_from_state
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt,
                messages=self.state.messages.copy(),
            )
            start_turn = self.state.turn_count

            # Restore context state if available
            if (
                self.context_management_enabled
                and self.context_manager
            ):
                if "context_stats" in self.state.metadata:
                    context_stats = self.state.metadata[
                        "context_stats"
                    ]
                    self.console.print(
                        f"[dim]Context usage at pause: "
                        f"Agent A: {context_stats['agent_a']['percentage']:.1f}%, "
                        f"Agent B: {context_stats['agent_b']['percentage']:.1f}%[/dim]"
                    )

            self.console.print(
                f"[green]Resuming conversation from turn {start_turn}[/green]\n"
            )
        else:
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt,
            )
            self.state = ConversationState(
                model_a=agent_a.model,
                model_b=agent_b.model,
                agent_a_id=agent_a.id,
                agent_b_id=agent_b.id,
                max_turns=max_turns,
                initial_prompt=initial_prompt,
                transcript_path=str(
                    self.transcript_manager.get_transcript_path()
                ),
            )
            start_turn = 0

        # Initial message (only if not resuming)
        if not resume_from_state:
            first_message = Message(
                role="user",
                content=initial_prompt,
                agent_id="researcher",  # Initial prompt is researcher guidance
            )
            self.conversation.messages.append(first_message)
            self.state.add_message(first_message)

            # Display it
            self.console.print(
                Panel(
                    initial_prompt,
                    title="[bold cyan]Researcher Note (Initial Prompt)[/bold cyan]",
                    border_style="cyan",
                )
            )
            self.console.print()

            # Display context window limits if enabled
            if (
                self.context_management_enabled
                and self.context_manager
            ):
                self.console.print(
                    "[bold cyan]Context Windows:[/bold cyan]"
                )
                for agent in [agent_a, agent_b]:
                    if (
                        agent.model
                        in self.context_manager.context_limits
                    ):
                        limit = self.context_manager.context_limits[
                            agent.model
                        ]
                        effective_limit = (
                            limit
                            - self.context_manager.reserved_tokens
                        )
                        self.console.print(
                            f"  • {agent.id} ({agent.model}): "
                            f"{effective_limit:,} tokens (total: {limit:,})"
                        )
                self.console.print()

        # Run conversation loop
        try:
            for turn in range(start_turn, max_turns):
                # Check for pause request - but don't break if conductor is handling it
                if self._pause_requested:
                    if (
                        hasattr(self, "conductor")
                        and self.conductor
                        and self.conductor.is_paused
                    ):
                        # Conductor is handling the pause - continue loop for interventions
                        self._pause_requested = False  # Reset flag
                        self.console.print(
                            "[yellow]🎼 Conductor paused - ready for interventions[/yellow]\n"
                        )
                    else:
                        # Regular pause - save and exit
                        await self._handle_pause()
                        break

                # PRIORITY 1: Check context window limits (what actually matters)
                context_should_pause = False
                if (
                    self.context_management_enabled
                    and self.context_manager
                    and len(self.conversation.messages) > 2
                ):
                    # Check both models for context usage
                    messages_dict = [
                        {"content": msg.content}
                        for msg in self.conversation.messages
                    ]

                    capacity_a = (
                        self.context_manager.get_remaining_capacity(
                            messages_dict, agent_a.model
                        )
                    )
                    capacity_b = (
                        self.context_manager.get_remaining_capacity(
                            messages_dict, agent_b.model
                        )
                    )

                    # Use the most constrained model
                    max_usage = max(
                        capacity_a["percentage"],
                        capacity_b["percentage"],
                    )
                    most_constrained = (
                        agent_a.model
                        if capacity_a["percentage"]
                        >= capacity_b["percentage"]
                        else agent_b.model
                    )

                    if max_usage >= self.context_warning_threshold:
                        turns_remaining = self.context_manager.predict_turns_remaining(
                            messages_dict, most_constrained
                        )
                        self.console.print(
                            f"\n[yellow bold]⚠️  Context Warning: {max_usage:.1f}% of context window used "
                            f"(~{turns_remaining} turns remaining)[/yellow bold]\n"
                        )

                        if (
                            max_usage
                            >= self.context_auto_pause_threshold
                        ):
                            self.console.print(
                                f"[red bold]🛑 Auto-pausing: Context window {max_usage:.1f}% full[/red bold]"
                            )
                            context_should_pause = True

                if context_should_pause:
                    self._pause_requested = True
                    continue

                # Agent A responds with streaming
                (
                    response_a,
                    interrupted_a,
                ) = await self._get_agent_response_streaming(
                    agent_a.id
                )
                if response_a is None:  # Rate limit pause requested
                    continue

                # No more complex interrupt handling - keep it simple

                # Handle system/mediator messages differently
                if self._is_system_message(response_a):
                    # System messages are added to conversation for both agents to see
                    self.conversation.messages.append(response_a)
                    self.state.add_message(response_a)
                    # Display the system message
                    self._display_message(
                        response_a, "", context_info=None
                    )
                    # Continue to next iteration - don't proceed with normal agent flow
                    continue
                else:
                    self.conversation.messages.append(response_a)
                    self.state.add_message(response_a)

                # Check context usage for Agent A after adding message
                context_info_a = None
                if (
                    self.context_management_enabled
                    and self.context_manager
                ):
                    messages_dict = [
                        {"content": msg.content}
                        for msg in self.conversation.messages
                    ]
                    capacity_a = (
                        self.context_manager.get_remaining_capacity(
                            messages_dict, agent_a.model
                        )
                    )
                    context_info_a = capacity_a

                    # Check if we should warn about context usage
                    if self.context_manager.should_warn(
                        messages_dict,
                        agent_a.model,
                        self.context_warning_threshold,
                    ):
                        turns_remaining = self.context_manager.predict_turns_remaining(
                            messages_dict, agent_a.model
                        )
                        self.console.print(
                            f"\n[yellow bold]⚠️  Context Warning ({agent_a.model}): "
                            f"{capacity_a['percentage']:.1f}% used, ~{turns_remaining} turns remaining[/yellow bold]\n"
                        )

                # Display Agent A response
                self._display_message(
                    response_a,
                    agent_a.model,
                    context_info=context_info_a,
                )

                # Check for auto-pause due to context limits before Agent B
                if (
                    self.context_management_enabled
                    and self.context_manager
                ):
                    if self.context_manager.should_pause(
                        messages_dict,
                        agent_a.model,
                        self.context_auto_pause_threshold,
                    ):
                        self.console.print(
                            f"[red bold]🛑 Auto-pausing: Context window {capacity_a['percentage']:.1f}% full "
                            f"for {agent_a.model}[/red bold]"
                        )
                        self._pause_requested = True
                        continue

                # Agent B responds with streaming
                (
                    response_b,
                    interrupted_b,
                ) = await self._get_agent_response_streaming(
                    agent_b.id
                )
                if response_b is None:  # Rate limit pause requested
                    continue

                # No more complex interrupt handling - keep it simple

                # Handle system/mediator messages differently
                if self._is_system_message(response_b):
                    # System messages are added to conversation for both agents to see
                    self.conversation.messages.append(response_b)
                    self.state.add_message(response_b)
                    # Display the system message
                    self._display_message(
                        response_b, "", context_info=None
                    )
                    # Continue to next iteration - don't proceed with normal agent flow
                    continue
                else:
                    self.conversation.messages.append(response_b)
                    self.state.add_message(response_b)

                # Check context usage for Agent B after adding message
                context_info_b = None
                if (
                    self.context_management_enabled
                    and self.context_manager
                ):
                    messages_dict = [
                        {"content": msg.content}
                        for msg in self.conversation.messages
                    ]
                    capacity_b = (
                        self.context_manager.get_remaining_capacity(
                            messages_dict, agent_b.model
                        )
                    )
                    context_info_b = capacity_b

                    # Check if we should warn about context usage
                    if self.context_manager.should_warn(
                        messages_dict,
                        agent_b.model,
                        self.context_warning_threshold,
                    ):
                        turns_remaining = self.context_manager.predict_turns_remaining(
                            messages_dict, agent_b.model
                        )
                        self.console.print(
                            f"\n[yellow bold]⚠️  Context Warning ({agent_b.model}): "
                            f"{capacity_b['percentage']:.1f}% used, ~{turns_remaining} turns remaining[/yellow bold]\n"
                        )

                    # Check for auto-pause due to context limits
                    if self.context_manager.should_pause(
                        messages_dict,
                        agent_b.model,
                        self.context_auto_pause_threshold,
                    ):
                        self.console.print(
                            f"[red bold]🛑 Auto-pausing: Context window {capacity_b['percentage']:.1f}% full "
                            f"for {agent_b.model}[/red bold]"
                        )
                        self._pause_requested = True

                # Display Agent B response
                self._display_message(
                    response_b,
                    agent_b.model,
                    context_info=context_info_b,
                )

                # Check for end-of-turn conductor intervention
                if hasattr(self, "conductor") and self.conductor:
                    # Create a turn object for conductor
                    current_turn = ConversationTurn(
                        agent_a_message=response_a,
                        agent_b_message=response_b,
                        turn_number=turn + 1,
                    )

                    # Get intervention if needed
                    intervention = self.conductor.get_intervention(
                        current_turn
                    )
                    if intervention:
                        # Add intervention to conversation
                        self.conversation.messages.append(
                            intervention
                        )
                        self.state.add_message(intervention)
                        # Display the intervention
                        self._display_message(
                            intervention, "", context_info=None
                        )

                # Auto-save transcript after each turn with metrics
                await self.transcript_manager.save(
                    self.conversation,
                    metrics=self._get_current_metrics(),
                )

                # Calculate convergence after both agents have responded
                self.current_convergence = (
                    self.convergence_calculator.calculate(
                        self.conversation.messages
                    )
                )

                # Track convergence history
                self.convergence_history.append(
                    {
                        "turn": turn + 1,
                        "score": self.current_convergence,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                # Calculate and track turn metrics for both messages
                for msg in [response_a, response_b]:
                    if not self._is_system_message(msg):
                        metrics = calculate_turn_metrics(msg.content)
                        self.turn_metrics["message_lengths"].append(
                            metrics["length"]
                        )
                        self.turn_metrics["sentence_counts"].append(
                            metrics["sentences"]
                        )
                        self.turn_metrics["word_diversity"].append(
                            metrics["word_diversity"]
                        )
                        self.turn_metrics["emoji_density"].append(
                            metrics["emoji_density"]
                        )

                        # Update phase detection
                        update_phase_detection(
                            self.phase_detection,
                            {
                                "convergence": self.current_convergence,
                                "emoji_density": metrics[
                                    "emoji_density"
                                ],
                            },
                            turn + 1,
                        )

                # Auto-pause at 90% convergence
                if (
                    self.current_convergence >= 0.90
                    and not self.auto_paused_at_convergence
                ):
                    self.auto_paused_at_convergence = True
                    self._pause_requested = True
                    self.console.print(
                        f"\n[red bold]⚠️  AUTO-PAUSE: Convergence reached {self.current_convergence:.2f}[/red bold]"
                    )
                    self.console.print(
                        "[yellow]Agents are highly synchronized. Consider intervention.[/yellow]\n"
                    )

                    # Show convergence trend if conductor is active
                    if (
                        hasattr(self, "conductor")
                        and self.conductor
                        and self.conductor.mode == "flowing"
                    ):
                        if hasattr(
                            self.conductor,
                            "display_convergence_trend",
                        ):
                            self.conductor.display_convergence_trend()

                # Reset auto-pause flag if convergence drops below 0.85 (hysteresis)
                elif self.current_convergence < 0.85:
                    self.auto_paused_at_convergence = False

                # Check for attractor detection
                message_contents = [
                    msg.content
                    for msg in self.conversation.messages
                    if msg.role != "system"
                ]

                # Show indicator when checking
                if (
                    self.attractor_manager.enabled
                    and (turn + 1)
                    % self.attractor_manager.check_interval
                    == 0
                ):
                    self.console.print(
                        "[dim]🔍 Checking for patterns...[/dim]",
                        end="",
                    )

                if attractor_result := self.attractor_manager.check(
                    message_contents, turn + 1, show_progress=False
                ):
                    self.console.print(
                        " [red bold]ATTRACTOR FOUND![/red bold]"
                    )
                    await self._handle_attractor_detection(
                        attractor_result
                    )
                    if attractor_result["action"] == "stop":
                        break
                elif (
                    self.attractor_manager.enabled
                    and (turn + 1)
                    % self.attractor_manager.check_interval
                    == 0
                ):
                    self.console.print(
                        " [green]continuing normally.[/green]"
                    )

                # Auto-checkpoint at intervals
                if (
                    self.checkpoint_enabled
                    and (turn + 1) % self.checkpoint_interval == 0
                ):
                    # Save context state in metadata if enabled
                    if (
                        self.context_management_enabled
                        and self.context_manager
                    ):
                        messages_dict = [
                            {"content": msg.content}
                            for msg in self.conversation.messages
                        ]
                        self.state.metadata["context_stats"] = {
                            "agent_a": self.context_manager.get_remaining_capacity(
                                messages_dict, agent_a.model
                            ),
                            "agent_b": self.context_manager.get_remaining_capacity(
                                messages_dict, agent_b.model
                            ),
                        }

                    if self.state:
                        checkpoint_path = self.state.save_checkpoint()
                        self.console.print(
                            f"[dim]Checkpoint saved: {checkpoint_path}[/dim]"
                        )

                # Show simple turn counter with key info
                if (turn + 1) % 5 == 0:  # Every 5 turns
                    status_parts = [f"Turn {turn + 1}/{max_turns}"]

                    # Add convergence if available
                    if self.current_convergence > 0:
                        emoji = (
                            " ⚠️"
                            if self.current_convergence >= 0.75
                            else ""
                        )
                        status_parts.append(
                            f"Conv: {self.current_convergence:.2f}{emoji}"
                        )

                    # Add context usage if enabled
                    if (
                        self.context_management_enabled
                        and self.context_manager
                    ):
                        messages_dict = [
                            {"content": msg.content}
                            for msg in self.conversation.messages
                        ]
                        capacity_a = self.context_manager.get_remaining_capacity(
                            messages_dict, agent_a.model
                        )
                        capacity_b = self.context_manager.get_remaining_capacity(
                            messages_dict, agent_b.model
                        )
                        max_usage = max(
                            capacity_a["percentage"],
                            capacity_b["percentage"],
                        )
                        if (
                            max_usage > 50
                        ):  # Only show when it matters
                            status_parts.append(
                                f"Context: {max_usage:.0f}%"
                            )

                    self.console.print(
                        f"\n[dim]{' | '.join(status_parts)} | Ctrl+C to pause[/dim]\n"
                    )
                else:
                    # Minimal turn counter every turn
                    self.console.print(
                        f"\n[dim]Turn {turn + 1}/{max_turns}[/dim]\n"
                    )

        except KeyboardInterrupt:
            # Handled by signal handler
            pass
        finally:
            # Restore original signal handler
            self._restore_signal_handler()

            # Save conductor intervention data if available
            if self.conductor:
                intervention_summary = (
                    self.conductor.get_intervention_summary()
                )
                if intervention_summary["total_interventions"] > 0:
                    self.state.metadata[
                        "conductor_interventions"
                    ] = intervention_summary
                    self.console.print(
                        f"\n[dim]Conductor interventions: "
                        f"{intervention_summary['interventions']} interventions[/dim]"
                    )

                # No cleanup needed for new conductor

            # Save final transcript with complete metrics
            await self.transcript_manager.save(
                self.conversation, metrics=self._get_current_metrics()
            )

    def _display_message(
        self,
        message: Message,
        model_name: str,
        context_info: Optional[Dict[str, Any]] = None,
    ):
        """Display a message in the terminal with Rich formatting."""

        # Simple two-way split
        if message.agent_id == "agent_a":
            title = f"[bold green]Agent A ({model_name})[/bold green]"
            border_style = "green"
        elif message.agent_id == "agent_b":
            title = (
                f"[bold magenta]Agent B ({model_name})[/bold magenta]"
            )
            border_style = "magenta"
        else:
            # Everything else is a researcher note
            title = "[bold cyan]Researcher Note[/bold cyan]"
            border_style = "cyan"

        self.console.print(
            Panel(
                message.content,
                title=title,
                border_style=border_style,
            )
        )
        self.console.print()

    async def _get_agent_response(self, agent_id: str) -> Message:
        """Get agent response."""
        if not self.conversation:
            raise ValueError("No conversation initialized")

        # Route through the router - use new method
        try:
            response = await self.router.get_next_response(
                self.conversation.messages, agent_id
            )
            return response
        except Exception as e:
            # Check if it's a rate limit error
            if "rate limit" in str(e).lower():
                self.console.print(
                    f"\n[red bold]⚠️  Hit actual rate limit: {e}[/red bold]"
                )
                self.console.print(
                    "[yellow]Saving checkpoint and pausing...[/yellow]"
                )
                await self._handle_pause()
                self.console.print(
                    "[green]Resume with: pidgin resume --latest[/green]"
                )
                raise SystemExit(0)  # Graceful exit
            else:
                # Other API errors
                self.console.print(f"\n[red]❌ API Error: {e}[/red]")
                await self._handle_pause()
                raise

    def _setup_signal_handler(self):
        """Set up minimal signal handler for Ctrl+C."""

        def interrupt_handler(signum, frame):
            # If we have a conductor, pause it
            if hasattr(self, "conductor") and self.conductor:
                self.conductor.is_paused = True
                self.console.print(
                    "\n[yellow]⏸️  Paused. Intervention available at next turn.[/yellow]"
                )
            else:
                # No conductor, just exit normally
                self.console.print("\n[red]Stopped by user[/red]")
                raise KeyboardInterrupt()

        # Only handle SIGINT (Ctrl+C), remove SIGTSTP handling
        self._original_sigint = signal.signal(
            signal.SIGINT, interrupt_handler
        )

        # Simple controls message
        self.console.print(
            "[dim]Press Ctrl+C anytime to pause[/dim]\n"
        )

    def _restore_signal_handler(self):
        """Restore original signal handler."""
        if (
            hasattr(self, "_original_sigint")
            and self._original_sigint
        ):
            signal.signal(signal.SIGINT, self._original_sigint)

    async def _handle_pause(self):
        """Handle pause request."""
        self.console.print(
            "\n[yellow]Pausing conversation...[/yellow]"
        )

        # Save context window state in metadata if enabled
        if self.context_management_enabled and self.context_manager:
            # Get both agents from the conversation
            agent_a = next(
                a
                for a in self.conversation.agents
                if a.id == "agent_a"
            )
            agent_b = next(
                a
                for a in self.conversation.agents
                if a.id == "agent_b"
            )

            self.state.metadata["context_stats"] = {
                "agent_a": self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agent_a.model
                ),
                "agent_b": self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agent_b.model
                ),
            }

        # Save conductor intervention data if available
        if hasattr(self, "conductor") and self.conductor:
            intervention_summary = (
                self.conductor.get_intervention_summary()
            )
            if intervention_summary["total_interventions"] > 0:
                self.state.metadata[
                    "conductor_interventions"
                ] = intervention_summary

        checkpoint_path = self.state.save_checkpoint()
        self.console.print(
            f"\n[green]Checkpoint saved: {checkpoint_path}[/green]"
        )
        self.console.print(
            f"[green]Resume with: pidgin resume {checkpoint_path}[/green]\n"
        )

    def _is_system_message(self, message: Message) -> bool:
        """Check if a message is from system, human, or mediator (non-agent sources)."""
        if hasattr(message, "source") and message.source:
            return message.source in [
                MessageSource.SYSTEM,
                MessageSource.HUMAN,
                MessageSource.MEDIATOR,
            ]
        # Fallback to agent_id check for backward compatibility
        return message.agent_id in [
            "system",
            "human",
            "mediator",
            "external",
        ]

    async def _handle_attractor_detection(
        self, result: Dict[str, Any]
    ):
        """Handle attractor detection event."""
        # Store for final summary
        self.attractor_detected = result

        # Clean, simplified output
        self.console.print()
        max_turns = self.state.max_turns if self.state else "?"
        self.console.print(
            f"[red bold]🎯 ATTRACTOR DETECTED - Turn {result['turn_detected']}/{max_turns}[/red bold]"
        )
        self.console.print(f"[yellow]Type:[/yellow] {result['type']}")
        self.console.print(
            f"[yellow]Pattern:[/yellow] {result['description']}"
        )
        self.console.print(
            f"[yellow]Confidence:[/yellow] {result['confidence']:.0%}"
        )
        if "typical_turns" in result:
            self.console.print(
                f"[yellow]Typical occurrence:[/yellow] Turn {result['typical_turns']}"
            )
        self.console.print()

        # Save attractor analysis
        self.console.print(
            "[dim]💾 Saving transcript with detection data...[/dim]"
        )
        if self.state and self.state.transcript_path:
            analysis_path = self.attractor_manager.save_analysis(
                Path(self.state.transcript_path)
            )
            if analysis_path:
                self.console.print(
                    f"[green]✅ Analysis saved to: {analysis_path}[/green]"
                )

        # Save the transcript with metadata and metrics
        if self.conversation:
            await self.transcript_manager.save(
                self.conversation, metrics=self._get_current_metrics()
            )
            transcript_path = (
                self.state.transcript_path
                if self.state
                else "unknown"
            )
            self.console.print(
                f"[green]✅ Transcript saved to: {transcript_path}[/green]"
            )

        # Show conversation analysis
        self.console.print("\n[cyan]📊 Conversation Analysis:[/cyan]")
        self.console.print(
            f"• Turns before attractor: {result['turn_detected']}"
        )
        self.console.print(f"• Attractor type: {result['type']}")
        self.console.print(
            f"• Trigger: Deep conversation → {result['type'].lower()}"
        )
        if "typical_turns" in result:
            self.console.print(
                f"• Notable: Detected at turn {result['turn_detected']} (typical: {result['typical_turns']})"
            )
        self.console.print()

        if result["action"] == "stop":
            self.console.print(
                "[red bold]Ending conversation - Structural attractor reached[/red bold]\n"
            )
        elif result["action"] == "pause":
            self._pause_requested = True

    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics for transcript saving."""
        # Conductor intervention data
        conductor_data = {}
        if hasattr(self, "conductor") and self.conductor:
            conductor_data = self.conductor.get_intervention_summary()

        return {
            "convergence_history": self.convergence_history,
            "turn_metrics": self.turn_metrics,
            "structural_patterns": {
                "current_convergence": self.current_convergence,
                "convergence_threshold": self.convergence_threshold,
                "auto_paused_at_convergence": self.auto_paused_at_convergence,
            },
            "phase_detection": self.phase_detection,
            "conductor_data": conductor_data,
        }

    async def _get_agent_response_streaming(
        self, agent_id: str
    ) -> Tuple[Optional[Message], bool]:
        """Stream response with simple status display."""

        if not self.conversation:
            raise ValueError("No conversation initialized")

        chunks = []

        # Get agent info for display
        agent_name = "Agent A" if agent_id == "agent_a" else "Agent B"
        status_color = "green" if agent_id == "agent_a" else "magenta"

        # Simple streaming with status
        with self.console.status(
            f"[bold {status_color}]{agent_name} is responding...[/bold {status_color}]",
            spinner="dots",
        ):
            try:
                async for chunk, _ in self.router.get_next_response_stream(  # type: ignore
                    self.conversation.messages, agent_id
                ):
                    chunks.append(chunk)

            except Exception as e:
                if "rate limit" in str(e).lower():
                    self.console.print(
                        f"\n[red]Rate limit hit: {e}[/red]"
                    )
                    await self._handle_pause()
                    return None, False
                else:
                    raise

        # Create message
        content = "".join(chunks)
        if not content:
            return None, False

        message = Message(
            role="assistant", content=content, agent_id=agent_id
        )

        return message, False  # Never interrupted for now
