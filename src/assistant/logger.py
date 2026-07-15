"""
Centralized logging for the Voice Assistant.

This module provides a single logger instance for the entire application.

Responsibilities
----------------
- Console logging
- File logging
- Structured latency logging (JSONL)
- High-resolution timing utility

No other module should configure Python's logging system directly.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from time import perf_counter

from .config_loader import Config
from .events import Event


class Logger:
    """
    Singleton logger used throughout the application.
    """

    _instance: Logger | None = None
    _initialized = False

    def __new__(cls) -> Logger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True

        config = Config()

        # ==========================================================
        # Log Directories
        # ==========================================================

        log_directory = Path(config.storage.logs_dir)
        log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._latency_log = Path(
            config.metrics.latency_log_file
        )

        self._latency_log.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ==========================================================
        # Standard Logger
        # ==========================================================

        self._logger = logging.getLogger(
            "voice_assistant"
        )

        self._logger.setLevel(
            config.logging.level
        )

        self._logger.propagate = False

        if not self._logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s"
            )

            if config.logging.console:

                console_handler = logging.StreamHandler()

                console_handler.setFormatter(
                    formatter
                )

                self._logger.addHandler(
                    console_handler
                )

            file_handler = logging.FileHandler(
                config.logging.log_file,
                encoding="utf-8",
            )

            file_handler.setFormatter(
                formatter
            )

            self._logger.addHandler(
                file_handler
            )

    # ==========================================================
    # Standard Logging
    # ==========================================================

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def critical(self, message: str) -> None:
        self._logger.critical(message)

    def exception(self, message: str) -> None:
        self._logger.exception(message)

    # ==========================================================
    # Event Logging
    # ==========================================================

    def event(self, event: Event) -> None:
        """
        Log a system event.
        """

        self.info(
            f"[EVENT] {event.value}"
        )

    # ==========================================================
    # Latency Logging
    # ==========================================================

    def latency(
        self,
        event: Event,
        start_time: float,
    ) -> None:
        """
        Record latency for a system event.
        """

        latency_ms = (
            perf_counter() - start_time
        ) * 1000

        record = {
            "timestamp": perf_counter(),
            "event": event.value,
            "latency_ms": round(
                latency_ms,
                2,
            ),
        }

        try:

            with self._latency_log.open(
                "a",
                encoding="utf-8",
            ) as file:

                file.write(
                    json.dumps(record)
                    + "\n"
                )

        except OSError:

            self._logger.exception(
                "Failed to write latency log."
            )

    # ==========================================================
    # Timing Utility
    # ==========================================================

    @staticmethod
    def time() -> float:
        """
        Return a high-resolution timestamp.

        Used throughout the project for latency
        measurements.
        """

        return perf_counter()


logger = Logger()