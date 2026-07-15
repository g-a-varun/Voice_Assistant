"""
Response manager for the Voice Assistant.

Converts streamed LLM tokens into natural text chunks suitable
for streaming Text-to-Speech synthesis.

The goal is to reduce perceived latency by allowing the TTS engine
to begin speaking before the language model has completed the
entire response.
"""

from __future__ import annotations

from typing import AsyncIterator

from .interfaces import (
    LLMToken,
    ResponseManager,
)


class DefaultResponseManager(ResponseManager):
    """
    Default implementation of the ResponseManager interface.
    """

    _SENTENCE_ENDINGS = (".", "!", "?", "\n")

    def __init__(self) -> None:
        self._buffer = ""

    # ==========================================================
    # Public API
    # ==========================================================

    async def process(
        self,
        token_stream: AsyncIterator[LLMToken],
    ) -> AsyncIterator[str]:
        """
        Convert streamed LLM tokens into speakable text chunks.

        A chunk is emitted whenever:
        - a sentence boundary is detected, or
        - the final token is received.
        """

        async for token in token_stream:

            self._buffer += token.text

            if self._should_flush(token):

                chunk = self._buffer.strip()

                if chunk:
                    yield chunk

                self._buffer = ""

        if self._buffer:

            chunk = self._buffer.strip()

            if chunk:
                yield chunk

        self.reset()

    def reset(self) -> None:
        """
        Clear any buffered response.
        """

        self._buffer = ""

    # ==========================================================
    # Internal Helpers
    # ==========================================================

    def _should_flush(
        self,
        token: LLMToken,
    ) -> bool:
        """
        Decide whether buffered text should be emitted.
        """

        if token.is_final:
            return True

        return self._buffer.endswith(
            self._SENTENCE_ENDINGS
        )