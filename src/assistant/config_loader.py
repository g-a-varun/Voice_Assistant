"""
Configuration loader for the Voice Assistant.

This module is the only component responsible for reading configuration
files from disk. All other modules should access configuration through
the Config class and must never read YAML files directly.

Configuration is exposed through immutable attribute access:

    config.audio.sample_rate
    config.llm.model_name
    config.prompts.system_prompt
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigNode:
    """
    Recursively converts dictionaries into objects that support
    attribute-style access.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                value = ConfigNode(value)
            elif isinstance(value, list):
                value = [
                    ConfigNode(item) if isinstance(item, dict) else item
                    for item in value
                ]

            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__!r})"


class Config:
    """
    Loads application configuration from YAML files.

    Example:
        config = Config()

        print(config.audio.sample_rate)
        print(config.llm.model_name)
        print(config.prompts.system_prompt)
    """

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]

        settings_path = project_root / "config" / "settings.yaml"
        prompts_path = project_root / "config" / "prompts.yaml"

        settings = self._load_yaml(settings_path)
        prompts = self._load_yaml(prompts_path)

        for key, value in settings.items():
            if isinstance(value, dict):
                value = ConfigNode(value)

            setattr(self, key, value)

        self.prompts = ConfigNode(prompts)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        """
        Load a YAML file.

        Raises:
            FileNotFoundError:
                If the file does not exist.

            ValueError:
                If the YAML is empty.
        """
        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if data is None:
            raise ValueError(
                f"Configuration file is empty: {path}"
            )

        return data