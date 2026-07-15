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

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


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
    Speech recognition result.
    """

    text: str
    confidence: float
    language: str
    is_final: bool


@dataclass(slots=True, frozen=True)
class LLMToken:
    """
    One streamed token from the language model.
    """

    text: str
    token_index: int
    is_first: bool = False
    is_final: bool = False


@dataclass(slots=True, frozen=True)
class ConversationTurn:
    """
    One message within a conversation.
    """

    role: Role
    text: str
    timestamp: float


@dataclass(slots=True)
class SessionContext:
    """
    Context supplied to the language model.

    Mutable because conversation history grows during
    a user session.
    """

    conversation_history: list[ConversationTurn] = field(
        default_factory=list
    )

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
        Return an asynchronous stream of audio frames.

        Implementations control buffering internally.
        """


# ============================================================================
# Voice Activity Detection
# ============================================================================


class VoiceActivityDetector(ABC):
    """
    Detects speech boundaries from incoming audio.
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

        Returns one of:

        - VADState.NONE
        - VADState.SPEECH_STARTED
        - VADState.SPEECH_ENDED
        """


# ============================================================================
# Speech-to-Text
# ============================================================================


class SpeechToText(ABC):
    """
    Streaming Speech-to-Text engine.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend implementation name."""

    @abstractmethod
    async def warmup(self) -> None:
        """
        Load models and prepare for inference.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True when the recognizer is ready.
        """

    @abstractmethod
    def transcribe_stream(
        self,
        frames: AsyncIterator[AudioFrame],
    ) -> AsyncIterator[Transcript]:
        """
        Convert streamed audio into streamed transcripts.

        Implementations may yield partial transcripts
        followed by a final transcript.
        """


# ============================================================================
# Conversation Management
# ============================================================================


class ConversationManager(ABC):
    """
    Maintains conversation history and builds the
    context supplied to the language model.
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
    def build_context(self) -> SessionContext:
        """
        Build the context that will be supplied to
        the language model.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Clear the current conversation.
        """


# ============================================================================
# Response Management
# ============================================================================


class ResponseManager(ABC):
    """
    Converts streamed LLM tokens into natural text
    chunks suitable for streaming TTS.
    """

    @abstractmethod
    def process(
        self,
        token_stream: AsyncIterator[LLMToken],
    ) -> AsyncIterator[str]:
        """
        Convert streamed LLM output into speakable
        text chunks.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Clear any buffered response state.
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
        Load the model and prepare it for inference.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True if the backend is healthy.
        """

    @abstractmethod
    def generate_stream(
        self,
        context: SessionContext,
    ) -> AsyncIterator[LLMToken]:
        """
        Generate a streamed response.

        The latest user message is expected to already be
        present inside the supplied SessionContext.
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
        Load voices and prepare the synthesis engine.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True if the engine is available.
        """

    @abstractmethod
    def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
    ) -> AsyncIterator[bytes]:
        """
        Convert streamed text into streamed PCM audio.

        The returned bytes should represent raw PCM chunks
        ready for playback.
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

        Implementations should begin playback as soon as
        the first chunk becomes available rather than waiting
        for the complete stream.
        """

    @abstractmethod
    async def interrupt(self) -> None:
        """
        Stop playback immediately.

        Used to support barge-in when the user begins speaking
        while the assistant is still responding.
        """

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """
        Return True while audio is actively playing.
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
        Return the path of the next fallback audio clip.

        The playback component is responsible for opening,
        decoding, and streaming the returned file.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the fallback rotation strategy.

        Called whenever a request completes successfully so
        the next interaction starts from a clean state.
        """

# ============================================================================
# End of Module
# ============================================================================

"""
Design Notes
============

This module defines the contracts used throughout the Voice Assistant.

Guidelines
----------
1. Concrete implementations must inherit only from the interfaces
   defined here.

2. The orchestrator should depend on these interfaces rather than
   implementation classes.

3. Implementations are free to use any backend (Faster-Whisper,
   Whisper.cpp, Ollama, Piper, ElevenLabs, etc.) provided they satisfy
   these contracts.

4. Any new interface added here should first be reflected in the
   architecture documentation before implementation.
"""