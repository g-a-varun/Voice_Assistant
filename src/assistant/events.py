"""
System-wide events used by the voice assistant.

This file is the single source of truth for every event that can flow
through the assistant.

Every module must publish only events defined here.

If a new event is introduced:
1. Add it here.
2. Update the architecture document.
3. Implement the handler inside the orchestrator.

Never use raw string literals elsewhere in the project.
"""

from enum import Enum


class Event(str, Enum):
    """System-wide events used by the orchestrator."""

    # ==================================================
    # System Lifecycle
    # ==================================================

    CONFIG_LOADED = "ConfigLoaded"
    MODELS_LOADED = "ModelsLoaded"

    SYSTEM_STARTED = "SystemStarted"
    SYSTEM_STOPPING = "SystemStopping"
    SYSTEM_STOPPED = "SystemStopped"

    # ==================================================
    # Audio
    # ==================================================

    AUDIO_STREAM_STARTED = "AudioStreamStarted"
    AUDIO_STREAM_STOPPED = "AudioStreamStopped"

    LISTENING_STARTED = "ListeningStarted"

    SPEECH_STARTED = "SpeechStarted"
    SPEECH_ENDED = "SpeechEnded"

    # ==================================================
    # Speech Recognition
    # ==================================================

    TRANSCRIPT_READY = "TranscriptReady"
    TRANSCRIPT_REJECTED = "TranscriptRejected"

    # ==================================================
    # Conversation
    # ==================================================

    PROMPT_BUILT = "PromptBuilt"

    # ==================================================
    # LLM
    # ==================================================

    LLM_FIRST_TOKEN_RECEIVED = "LLMFirstTokenReceived"
    LLM_COMPLETED = "LLMCompleted"
    LLM_FAILED = "LLMFailed"

    # ==================================================
    # Watchdog / Fallback
    # ==================================================

    WATCHDOG_TIMEOUT = "WatchdogTimeout"

    FALLBACK_AUDIO_STARTED = "FallbackAudioStarted"
    FALLBACK_AUDIO_FINISHED = "FallbackAudioFinished"

    # ==================================================
    # Response
    # ==================================================

    RESPONSE_VALIDATED = "ResponseValidated"

    # ==================================================
    # Text-to-Speech
    # ==================================================

    TTS_FIRST_CHUNK_READY = "TTSFirstChunkReady"

    # ==================================================
    # Playback
    # ==================================================

    PLAYBACK_STARTED = "PlaybackStarted"
    USER_INTERRUPTED = "UserInterrupted"
    PLAYBACK_FINISHED = "PlaybackFinished"

    # ==================================================
    # Error Handling
    # ==================================================

    ERROR_CAUGHT = "ErrorCaught"

    @classmethod
    def values(cls) -> list[str]:
        """Return all event names."""
        return [event.value for event in cls]