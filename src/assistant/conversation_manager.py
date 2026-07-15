"""
Conversation manager for the Voice Assistant.

Responsibilities
----------------
- Maintain conversation history
- Trim history to the configured size
- Build SessionContext objects for the LLM
- Reset conversations

This module never:
- Calls the LLM
- Generates responses
- Handles events
- Performs prompt engineering
"""

from __future__ import annotations

from .config_loader import Config
from .interfaces import (
    ConversationManager,
    ConversationTurn,
    Role,
    SessionContext,
)
from .logger import logger


class DefaultConversationManager(ConversationManager):
    """
    Default implementation of the ConversationManager interface.
    """

    def __init__(self) -> None:
        config = Config()

        self._system_prompt = config.prompts.system_prompt
        self._max_history_turns = config.conversation.history_turns

        self._history: list[ConversationTurn] = []

    # ==========================================================
    # Conversation Management
    # ==========================================================

    def add_turn(
        self,
        role: Role,
        text: str,
    ) -> None:
        """
        Add a conversation turn.

        Empty or whitespace-only messages are ignored.
        """

        text = text.strip()

        if not text:
            return

        self._history.append(
            ConversationTurn(
                role=role,
                text=text,
                timestamp=logger.time(),
            )
        )

        self._trim_history()

    def build_context(self) -> SessionContext:
        """
        Build the conversation context supplied to the language model.
        """

        return SessionContext(
            conversation_history=self._history.copy(),
            system_prompt=self._system_prompt,
            max_history_turns=self._max_history_turns,
        )

    def reset(self) -> None:
        """
        Clear the current conversation.
        """

        self._history.clear()

    # ==========================================================
    # Internal Helpers
    # ==========================================================

    def _trim_history(self) -> None:
        """
        Keep only the configured number of conversation turns.

        One turn consists of:
            User message
            Assistant response

        Therefore the maximum number of stored messages is
        history_turns × 2.
        """

        max_messages = self._max_history_turns * 2

        if len(self._history) <= max_messages:
            return

        self._history = self._history[-max_messages:]

    # ==========================================================
    # Read-Only Properties
    # ==========================================================

    @property
    def history(self) -> tuple[ConversationTurn, ...]:
        """
        Read-only conversation history.
        """

        return tuple(self._history)

    @property
    def turn_count(self) -> int:
        """
        Return the current number of stored messages.
        """

        return len(self._history)

    @property
    def is_empty(self) -> bool:
        """
        Return True if the conversation contains no messages.
        """

        return not self._history