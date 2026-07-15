"""
Configuration models and loader for the Voice Assistant.

This module is the single source of truth for application
configuration. Every module should obtain configuration through
the Config class instead of reading YAML files directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# ============================================================================
# Application
# ============================================================================


@dataclass(frozen=True)
class AppConfig:
    """Application metadata."""

    name: str
    version: str
    environment: str


# ============================================================================
# Storage
# ============================================================================


@dataclass(frozen=True)
class StorageConfig:
    """Project storage locations."""

    logs_dir: str
    assets_dir: str
    fallback_clips_dir: str
    session_db: str


# ============================================================================
# Audio
# ============================================================================


@dataclass(frozen=True)
class VADConfig:
    """Voice Activity Detection configuration."""

    engine: str
    threshold: float
    min_speech_ms: int
    min_silence_ms: int
    barge_in_enabled: bool
    barge_in_grace_ms: int


@dataclass(frozen=True)
class AudioConfig:
    """Microphone configuration."""

    sample_rate: int
    channels: int
    frame_duration_ms: int
    chunk_size: int
    input_device: str
    vad: VADConfig


# ============================================================================
# Speech-to-Text
# ============================================================================


@dataclass(frozen=True)
class DecodingConfig:
    """Decoder configuration."""

    beam_size: int


@dataclass(frozen=True)
class STTConfig:
    """Speech-to-Text configuration."""

    engine: str
    model_name: str
    language: str
    device: str
    compute_type: str
    decoding: DecodingConfig
    confidence_threshold: float


# ============================================================================
# Conversation
# ============================================================================


@dataclass(frozen=True)
class ConversationConfig:
    """Conversation history configuration."""

    history_turns: int
    max_user_message_chars: int


# ============================================================================
# Large Language Model
# ============================================================================


@dataclass(frozen=True)
class LLMConfig:
    """LLM configuration."""

    provider: str
    base_url: str
    model_name: str
    stream: bool
    temperature: float
    max_tokens: int
    request_timeout_ms: int
    retry_on_failure: int
    system_prompt_path: str


# ============================================================================
# Text-to-Speech
# ============================================================================


@dataclass(frozen=True)
class TTSConfig:
    """Text-to-Speech configuration."""

    engine: str
    voice: str
    sample_rate: int
    output_device: str
    streaming_chunk_ms: int


# ============================================================================
# Playback
# ============================================================================


@dataclass(frozen=True)
class PlaybackConfig:
    """Audio playback configuration."""

    interruptible: bool
    fade_out_ms: int


# ============================================================================
# Watchdog
# ============================================================================


@dataclass(frozen=True)
class WatchdogConfig:
    """Watchdog configuration."""

    timeout_ms: int
    fallback_clips_source: str
    rotation_strategy: str
    max_fallback_loops: int


# ============================================================================
# Error Recovery
# ============================================================================


@dataclass(frozen=True)
class ErrorRecoveryConfig:
    """Recovery behavior."""

    recovery_phrases_source: str
    return_to_state: str


# ============================================================================
# Logging
# ============================================================================


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    level: str
    console: bool
    log_file: str


# ============================================================================
# Metrics
# ============================================================================


@dataclass(frozen=True)
class MetricsConfig:
    """Performance metrics configuration."""

    enabled: bool
    latency_log_file: str


# ============================================================================
# Prompt Models
# ============================================================================


@dataclass(frozen=True)
class FallbackFiller:
    """Fallback filler phrase."""

    id: str
    text: str


@dataclass(frozen=True)
class ConfirmationPrompts:
    """Confirmation responses."""

    positive: list[str]
    negative: list[str]


@dataclass(frozen=True)
class PromptsConfig:
    """Prompt configuration."""

    system_prompt: str

    greetings: list[str]
    goodbyes: list[str]

    fallback_fillers: list[FallbackFiller]

    recovery_phrases: list[str]

    low_confidence_prompts: list[str]

    clarification_prompts: list[str]

    timeout_prompts: list[str]

    unsupported_request_prompts: list[str]

    confirmation_prompts: ConfirmationPrompts

# ============================================================================
# Configuration Loader
# ============================================================================


class Config:
    """
    Strongly typed application configuration.

    This class loads both settings.yaml and prompts.yaml exactly once
    and exposes their contents through strongly typed dataclasses.
    """

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]

        settings_path = project_root / "config" / "settings.yaml"
        prompts_path = project_root / "config" / "prompts.yaml"

        settings = self._load_yaml(settings_path)
        prompts = self._load_yaml(prompts_path)

        # ==========================================================
        # Application
        # ==========================================================

        self.app = AppConfig(**settings["app"])

        # ==========================================================
        # Storage
        # ==========================================================

        self.storage = StorageConfig(**settings["storage"])

        # ==========================================================
        # Audio
        # ==========================================================

        self.audio = AudioConfig(
            sample_rate=settings["audio"]["sample_rate"],
            channels=settings["audio"]["channels"],
            frame_duration_ms=settings["audio"]["frame_duration_ms"],
            chunk_size=settings["audio"]["chunk_size"],
            input_device=settings["audio"]["input_device"],
            vad=VADConfig(**settings["audio"]["vad"]),
        )

        # ==========================================================
        # Speech-to-Text
        # ==========================================================

        self.stt = STTConfig(
            engine=settings["stt"]["engine"],
            model_name=settings["stt"]["model_name"],
            language=settings["stt"]["language"],
            device=settings["stt"]["device"],
            compute_type=settings["stt"]["compute_type"],
            decoding=DecodingConfig(**settings["stt"]["decoding"]),
            confidence_threshold=settings["stt"]["confidence_threshold"],
        )

        # ==========================================================
        # Conversation
        # ==========================================================

        self.conversation = ConversationConfig(
            **settings["conversation"]
        )

        # ==========================================================
        # LLM
        # ==========================================================

        self.llm = LLMConfig(**settings["llm"])

        # ==========================================================
        # Text-to-Speech
        # ==========================================================

        self.tts = TTSConfig(**settings["tts"])

        # ==========================================================
        # Playback
        # ==========================================================

        self.playback = PlaybackConfig(**settings["playback"])

        # ==========================================================
        # Watchdog
        # ==========================================================

        self.watchdog = WatchdogConfig(**settings["watchdog"])

        # ==========================================================
        # Error Recovery
        # ==========================================================

        self.error_recovery = ErrorRecoveryConfig(
            **settings["error_recovery"]
        )

        # ==========================================================
        # Logging
        # ==========================================================

        self.logging = LoggingConfig(**settings["logging"])

        # ==========================================================
        # Metrics
        # ==========================================================

        self.metrics = MetricsConfig(**settings["metrics"])

        # ==========================================================
        # Prompts
        # ==========================================================

        self.prompts = PromptsConfig(
            system_prompt=prompts["system_prompt"],
            greetings=prompts["greetings"],
            goodbyes=prompts["goodbyes"],
            fallback_fillers=[
                FallbackFiller(**item)
                for item in prompts["fallback_fillers"]
            ],
            recovery_phrases=prompts["recovery_phrases"],
            low_confidence_prompts=prompts["low_confidence_prompts"],
            clarification_prompts=prompts["clarification_prompts"],
            timeout_prompts=prompts["timeout_prompts"],
            unsupported_request_prompts=prompts[
                "unsupported_request_prompts"
            ],
            confirmation_prompts=ConfirmationPrompts(
                **prompts["confirmation_prompts"]
            ),
        )

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        """
        Load a YAML configuration file.

        Args:
            path:
                Path to the YAML file.

        Returns:
            Parsed YAML as a dictionary.

        Raises:
            FileNotFoundError:
                If the configuration file does not exist.

            ValueError:
                If the YAML file is empty.
        """

        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data: dict[str, Any] | None = yaml.safe_load(file)

        if data is None:
            raise ValueError(
                f"Configuration file is empty: {path}"
            )

        return data