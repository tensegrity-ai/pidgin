"""Test model for offline development and testing."""

import hashlib
from collections.abc import AsyncGenerator
from typing import List, Optional

from ..core.types import Message
from .base import Provider, ResponseChunk


class LocalTestModel(Provider):
    """Deterministic test model that simulates conversation dynamics."""

    def __init__(self, responses=None):
        """Initialize test model with response patterns."""
        if responses is not None:
            # If custom responses are provided, use them in a simple cycle
            self.custom_responses = responses
            self.custom_response_index = 0
            self.responses = self._load_response_patterns()
        else:
            self.custom_responses = None
            self.responses = self._load_response_patterns()

    def _load_response_patterns(self) -> dict:
        """Load response patterns from bundled data."""
        return {
            "greetings": [
                "Hello! I'm a test model designed for offline experimentation.",
                "Greetings! I provide deterministic responses for testing.",
                "Hi there! I help test conversation patterns without API calls.",
            ],
            "questions": [
                "That's an interesting question. Let me think about that.",
                "I see what you're asking. Here's my perspective:",
                "Good question! Based on our discussion so far:",
            ],
            "agreements": [
                "I agree with your point.",
                "Yes, that makes sense.",
                "Absolutely, I see what you mean.",
            ],
            "elaborations": [
                "Building on that idea, we might consider",
                "To expand on this further,",
                "Following that line of thought,",
            ],
            "convergence": ["Indeed.", "Agreed.", "Precisely.", "Yes."],
        }

    async def stream_response(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        thinking_enabled: Optional[bool] = None,
        thinking_budget: Optional[int] = None,
    ) -> AsyncGenerator[ResponseChunk, None]:
        """Stream response chunks from the model.

        Args:
            messages: Conversation history
            temperature: Temperature setting (ignored for deterministic model)
            thinking_enabled: Thinking mode (ignored for test model)
            thinking_budget: Thinking budget (ignored for test model)

        Yields:
            Response chunks
        """
        # Generate the full response
        response = await self.generate(messages, temperature)

        # Yield the response as a single chunk (simulating streaming)
        yield ResponseChunk(response, "response")

    async def generate(
        self, messages: List[Message], temperature: Optional[float] = None
    ) -> str:
        """Generate a response based on conversation context.

        Args:
            messages: Conversation history
            temperature: Temperature setting (ignored for deterministic model)

        Returns:
            Generated response
        """
        # If custom responses are provided, cycle through them
        if self.custom_responses:
            response = self.custom_responses[
                self.custom_response_index % len(self.custom_responses)
            ]
            self.custom_response_index += 1
            return response

        if not messages:
            return self._get_greeting()

        # Analyze conversation state
        turn_count = len([m for m in messages if m.role == "assistant"])
        last_message = messages[-1].content.lower()

        # Convergence behavior after many turns
        if turn_count > 10:
            return self._get_convergence_response(turn_count)

        # Detect question
        if any(q in last_message for q in ["?", "what", "how", "why", "when", "where"]):
            return self._get_question_response(last_message)

        # Detect agreement signals
        if any(
            a in last_message for a in ["yes", "agree", "right", "exactly", "correct"]
        ):
            return self._get_agreement_response(turn_count)

        # Default to elaboration
        return self._get_elaboration_response(last_message, turn_count)

    def _get_greeting(self) -> str:
        """Get opening response."""
        return self.responses["greetings"][0]

    def _get_convergence_response(self, turn_count: int) -> str:
        """Get convergence response (short agreements)."""
        # Use turn count for deterministic variety
        index = turn_count % len(self.responses["convergence"])
        return self.responses["convergence"][index]

    def _get_question_response(self, prompt: str) -> str:
        """Get response to a question."""
        # Hash prompt for deterministic selection
        # MD5 is fine here - not used for security, just deterministic selection
        hash_val = int(
            hashlib.md5(prompt.encode(), usedforsecurity=False).hexdigest()[:8], 16
        )  # nosec B324
        questions = self.responses["questions"]
        base = questions[hash_val % len(questions)]

        # Add some content based on the question
        if "pattern" in prompt:
            return f"{base} I notice we're discussing patterns in our conversation."
        elif "test" in prompt:
            return f"{base} As a test model, I provide consistent responses for experimentation."
        elif "convergence" in prompt:
            return f"{base} Convergence is an interesting phenomenon where responses become shorter and more aligned."
        else:
            return f"{base} Let me share some thoughts on this topic."

    def _get_agreement_response(self, turn_count: int) -> str:
        """Get agreement response."""
        index = turn_count % len(self.responses["agreements"])
        return self.responses["agreements"][index]

    def _get_elaboration_response(self, last_message: str, turn_count: int) -> str:
        """Get elaboration response."""
        base = self.responses["elaborations"][
            turn_count % len(self.responses["elaborations"])
        ]

        # Add contextual elaboration based on message length
        word_count = len(last_message.split())
        if word_count < 10:
            return f"{base} perhaps we could explore this topic in more depth."
        elif word_count > 50:
            return f"{base} I appreciate the detailed perspective you've shared."
        else:
            return f"{base} the points you've raised connect to broader themes in our discussion."
