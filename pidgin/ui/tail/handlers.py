"""Event handlers for tail display."""

from typing import Dict, Optional

from rich.console import Console
from rich.text import Text

from ...core.events import (
    APIErrorEvent,
    ContextTruncationEvent,
    ConversationEndEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    ConversationStartEvent,
    InterruptRequestEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    MessageRequestEvent,
    ProviderTimeoutEvent,
    RateLimitPaceEvent,
    SystemPromptEvent,
    TokenUsageEvent,
    TurnCompleteEvent,
    TurnStartEvent,
)
from .constants import NORD_CYAN, NORD_GRAY, NORD_PURPLE
from .formatters import TailFormatter


class EventHandlers:
    """Handles display of different event types."""

    def __init__(self, console: Optional[Console]):
        """Initialize handlers.

        Args:
            console: Rich console for output (None for daemon mode)
        """
        self.console = console
        self.formatter = TailFormatter()
        self.agent_display_names: Dict[str, str] = {}

    def _print(self, *args, **kwargs) -> None:
        """Print to console if available (not in daemon mode)."""
        if self.console is not None:
            self.console.print(*args, **kwargs)

    def display_conversation_start(
        self, event: ConversationStartEvent, header: Text, color: str
    ) -> None:
        """Display conversation start event."""
        # Store agent display names for later use
        if event.agent_a_display_name:
            self.agent_display_names["agent_a"] = event.agent_a_display_name
        if event.agent_b_display_name:
            self.agent_display_names["agent_b"] = event.agent_b_display_name

        # Format as single line with key info
        content = f"id: {event.conversation_id[:12]}... | "
        content += f"{event.agent_a_model} ↔ {event.agent_b_model} | "
        content += f"max_turns: {event.max_turns}"

        self._print(header, content)

        # Show initial prompt on next line if present
        if event.initial_prompt:
            # Get human tag from config
            from ...config import Config

            config = Config()
            human_tag = config.get("defaults.human_tag", "")

            # Format prompt as agents see it
            if human_tag:
                full_prompt = f"{human_tag}: {event.initial_prompt}"
            else:
                full_prompt = event.initial_prompt

            prompt_truncated = full_prompt.strip().replace("\n", " ")
            if len(prompt_truncated) > 130:
                prompt_truncated = prompt_truncated[:127] + "..."

            prompt_header = Text()
            prompt_header.append(
                f"[{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}] ",
                style=NORD_GRAY,
            )
            prompt_header.append("◆ InitialPrompt", style=NORD_CYAN + " bold")

            self._print(prompt_header, prompt_truncated)

    def display_conversation_end(
        self, event: ConversationEndEvent, header: Text, color: str
    ) -> None:
        """Display conversation end event."""
        # Format reason nicely
        reason_map = {
            "high_convergence": "convergence",
            # Other reasons display as-is
        }
        reason_display = reason_map.get(event.reason, event.reason)

        # Format duration
        duration_str = ""
        if hasattr(event, "duration_ms") and event.duration_ms:
            duration_s = event.duration_ms / 1000
            if duration_s < 60:
                duration_str = f"{duration_s:.1f}s"
            else:
                minutes = int(duration_s // 60)
                seconds = int(duration_s % 60)
                duration_str = f"{minutes}m {seconds}s"

        # Format as single line
        content = f"reason: {reason_display} | turns: {event.total_turns}"
        if duration_str:
            content += f" | duration: {duration_str}"

        self._print(header, content)

    def display_turn_start(self, event: TurnStartEvent, header: Text) -> None:
        """Display turn start event."""
        self._print(header, f"Turn {event.turn_number}")

    def display_turn_complete(self, event: TurnCompleteEvent, header: Text) -> None:
        """Display turn complete event."""
        content = f"turn: {event.turn_number}"
        if event.convergence_score is not None:
            content += f" | convergence: {event.convergence_score:.3f}"
        self._print(header, content)

    def display_message_request(self, event: MessageRequestEvent, header: Text) -> None:
        """Display message request event."""
        self._print(
            header, f"{self.formatter.format_agent_id(event.agent_id)} thinking..."
        )

    def display_message_complete(
        self, event: MessageCompleteEvent, header: Text, color: str
    ) -> None:
        """Display message complete event."""
        # Get message content
        msg_content = (
            event.message.content
            if hasattr(event.message, "content")
            else str(event.message)
        )

        # Truncate message to first line, max 40 chars
        msg_lines = msg_content.strip().replace("\n", " ").split()
        truncated_msg = " ".join(msg_lines)
        if len(truncated_msg) > 40:
            truncated_msg = truncated_msg[:37] + "..."

        # Build metadata
        metadata = []
        if hasattr(event, "duration_ms") and event.duration_ms is not None:
            metadata.append(f"{event.duration_ms / 1000:.1f}s")
        if hasattr(event, "tokens_used") and event.tokens_used:
            metadata.append(f"{event.tokens_used}tok")

        # Format as single line
        content = f"{self.formatter.format_agent_id(event.agent_id)}: {truncated_msg}"
        if metadata:
            content += f" [{NORD_GRAY}]({' | '.join(metadata)})[/{NORD_GRAY}]"

        self._print(header, content)

    def handle_message_chunk(self, event: MessageChunkEvent) -> None:
        """Handle message chunks."""
        # Get chunk content with correct attribute name
        chunk_content = (
            event.chunk if hasattr(event, "chunk") else getattr(event, "content", "")
        )

        # Format as single line with timestamp
        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        header = Text()
        header.append(f"[{timestamp}] ", style=NORD_GRAY)
        header.append("· MessageChunk", style=NORD_PURPLE + " bold")

        # Truncate chunk to 20 chars
        truncated_chunk = chunk_content.strip().replace("\n", " ")
        if len(truncated_chunk) > 40:
            truncated_chunk = truncated_chunk[:37] + "..."

        content = f"{self.formatter.format_agent_id(event.agent_id)}: {truncated_chunk}"
        self._print(header, content)

    def display_api_error(self, event: APIErrorEvent, header: Text, color: str) -> None:
        """Display API error event."""
        error_type = getattr(event, "error_type", "Unknown")
        error_msg = str(event.error_message)

        # Truncate error message if too long
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."

        content = f"type: {error_type} | {error_msg}"
        self._print(header, content)

    def display_context_truncation(
        self, event: ContextTruncationEvent, header: Text, color: str
    ) -> None:
        """Display context truncation event."""
        content = f"agent: {self.formatter.format_agent_id(event.agent_id)} | "
        content += f"dropped: {event.messages_dropped} messages | "
        content += f"original: {event.original_message_count}"
        self._print(header, content)

    def display_system_prompt(self, event: SystemPromptEvent, header: Text) -> None:
        """Display system prompt event."""
        # Truncate prompt for display
        prompt_lines = event.prompt.strip().split("\n")
        if len(prompt_lines) > 1:
            display_prompt = prompt_lines[0][:50] + "..."
        else:
            display_prompt = prompt_lines[0]
            if len(display_prompt) > 80:
                display_prompt = display_prompt[:77] + "..."

        content = f"agent: {self.formatter.format_agent_id(event.agent_id)} | {display_prompt}"
        self._print(header, content)

    def display_rate_limit(self, event: RateLimitPaceEvent, header: Text) -> None:
        """Display rate limit event."""
        wait_time = event.wait_time
        content = f"provider: {event.provider} | waiting: {wait_time:.1f}s"

        if hasattr(event, "reason") and event.reason:
            content += f" | reason: {event.reason}"

        self._print(header, content)

    def display_token_usage(self, event: TokenUsageEvent, header: Text) -> None:
        """Display token usage event."""
        content = f"provider: {event.provider} | "
        content += f"tokens: {event.tokens_used:,} | "
        content += f"rate: {event.current_usage_rate:.1f}/min | "
        content += f"limit: {event.tokens_per_minute_limit:,}/min"

        if hasattr(event, "cost_cents") and event.cost_cents:
            content += f" | cost: ${event.cost_cents / 100:.3f}"

        self._print(header, content)

    def display_provider_timeout(
        self, event: ProviderTimeoutEvent, header: Text
    ) -> None:
        """Display provider timeout event."""
        content = f"provider: {event.provider} | timeout: {event.timeout_seconds:.1f}s"
        if hasattr(event, "attempt") and event.attempt:
            content += f" | attempt: {event.attempt}"
        self._print(header, content)

    def display_interrupt_request(
        self, event: InterruptRequestEvent, header: Text
    ) -> None:
        """Display interrupt request event."""
        content = f"source: {event.interrupt_source} | turn: {event.turn_number}"
        self._print(header, content)

    def display_conversation_paused(
        self, event: ConversationPausedEvent, header: Text
    ) -> None:
        """Display conversation paused event."""
        content = f"paused during: {event.paused_during} | turn: {event.turn_number}"
        self._print(header, content)

    def display_conversation_resumed(
        self, event: ConversationResumedEvent, header: Text
    ) -> None:
        """Display conversation resumed event."""
        content = f"turn: {event.turn_number}"
        self._print(header, content)
