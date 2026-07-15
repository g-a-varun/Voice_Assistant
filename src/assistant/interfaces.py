"""
Module interfaces (contracts) for the Voice Assistant.

Every concrete implementation (Faster-Whisper, Ollama, Piper, etc.)
must implement these interfaces. This allows implementations to be
replaced without changing the orchestrator or other modules.

This file is the single source of truth for all module contracts.

Do not modify these interfaces casually. Any change here affects
every implementation in the project.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import AsyncIterator


# ============================================================================
# Enums
# ============================================================================


class Role(str, Enum):
    """Conversation participant."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class VADState(Enum):
    """Voice Activity Detection state."""

    NONE = auto()
    SPEECH_STARTED = auto()
    SPEECH_ENDED = auto()


# ============================================================================
# Shared Data Models
# ============================================================================


@dataclass(slots=True, frozen=True)
class AudioFrame:
    """
    Raw PCM audio captured from the microphone.
    """

    data: bytes
    sample_rate: int
    channels: int
    timestamp: float


@dataclass(slots=True, frozen=True)
class Transcript:
    """
    Result produced by the Speech-to-Text engine.
    """

    text: str
    confidence: float
    language: str
    is_final: bool


@dataclass(slots=True, frozen=True)
class LLMToken:
    """
    Single streamed token from the language model.
    """

    text: str
    token_index: int
    is_first: bool = False
    is_final: bool = False


@dataclass(slots=True, frozen=True)
class ConversationTurn:
    """
    One conversation message.
    """

    role: Role
    text: str
    timestamp: float


@dataclass(slots=True)
class SessionContext:
    """
    Context supplied to the language model.

    Mutable because conversation history grows throughout the session.
    """

    conversation_history: list[ConversationTurn] = field(default_factory=list)
    system_prompt: str = ""
    max_history_turns: int = 6


# ============================================================================
# Audio Input
# ============================================================================


class AudioInput(ABC):
    """
    Captures audio from the microphone.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    async def start(self) -> None:
        """Start microphone capture."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop microphone capture."""

    @abstractmethod
    def frames(self) -> AsyncIterator[AudioFrame]:
        """
        Yield audio frames continuously.

        The implementation controls buffering internally.
        """


# ============================================================================
# Voice Activity Detection
# ============================================================================


class VoiceActivityDetector(ABC):
    """
    Detects speech boundaries.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    def process(
        self,
        frame: AudioFrame,
    ) -> VADState:
        """
        Process one audio frame.

        Returns:
            VADState.NONE
            VADState.SPEECH_STARTED
            VADState.SPEECH_ENDED
        """


# ============================================================================
# Speech-to-Text
# ============================================================================


class SpeechToText(ABC):
    """
    Streaming speech recognizer.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    async def warmup(self) -> None:
        """
        Load the recognition model and perform any required warm-up.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True if the recognizer is ready.
        """

    @abstractmethod
    async def transcribe_stream(
        self,
        frames: AsyncIterator[AudioFrame],
    ) -> AsyncIterator[Transcript]:
        """
        Stream transcripts from incoming audio frames.

        Implementations may yield partial transcripts followed
        by one final transcript.
        """

# ============================================================================
# Conversation Management
# ============================================================================


class ConversationManager(ABC):
    """
    Maintains conversation history and builds the context supplied
    to the language model.
    """

    @abstractmethod
    def add_turn(
        self,
        role: Role,
        text: str,
    ) -> None:
        """
        Add one conversation turn.
        """

    @abstractmethod
    def build_context(
        self,
        latest_user_message: str,
    ) -> SessionContext:
        """
        Build the conversation context that will be sent to the LLM.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Clear the current conversation.
        """


# ============================================================================
# Large Language Model
# ============================================================================


class LLMEngine(ABC):
    """
    Streaming Large Language Model.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    async def warmup(self) -> None:
        """
        Load the model and perform any warm-up work.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True if the backend is healthy.
        """

    @abstractmethod
    async def generate_stream(
        self,
        context: SessionContext,
        user_text: str,
    ) -> AsyncIterator[LLMToken]:
        """
        Stream generated tokens.
        """


# ============================================================================
# Text-to-Speech
# ============================================================================


class TextToSpeech(ABC):
    """
    Streaming Text-to-Speech engine.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    async def warmup(self) -> None:
        """
        Warm up the synthesis engine.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True if the engine is available.
        """

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
    ) -> AsyncIterator[bytes]:
    """
        Convert streamed text into streamed PCM audio.
    """


# ============================================================================
# Audio Playback
# ============================================================================


class AudioPlayback(ABC):
    """
    Plays streamed audio to the output device.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    async def play_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
    ) -> None:
        """
        Play streamed PCM audio.
        """

    @abstractmethod
    async def interrupt(self) -> None:
        """
        Stop playback immediately.
        """

    @abstractmethod
    def is_playing(self) -> bool:
        """
        Return True while playback is active.
        """


# ============================================================================
# Fallback Provider
# ============================================================================


class FallbackProvider(ABC):
    """
    Supplies pre-generated filler clips used while waiting for
    the language model.
    """

    @abstractmethod
    def next_clip(self) -> Path:
        """
        Return the path to the next fallback audio clip.
        """