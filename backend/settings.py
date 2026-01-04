"""Settings management for voice agent configuration."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULT_GREETINGS = [
    "Hello! How can I help you today?",
    "Hi there! What can I do for you?",
    "Hey! I'm ready to assist you.",
]


@dataclass
class AgentSettings:
    """Voice agent configuration settings."""

    # Agent identity
    agent_name: str = "Geveze"

    # TTS settings
    tts_voice: str = "jenny_dioco"
    tts_voice_tr: str = "fahrettin"
    tts_model: str = "speaches-ai/piper-en_GB-jenny_dioco-medium"
    tts_model_tr: str = "speaches-ai/piper-tr_TR-fahrettin-medium"
    tts_speed: float = 1.0

    # STT settings
    stt_model: str = "Systran/faster-whisper-medium"

    # LLM settings
    llm_model: str = "ministral-3:8b"
    temperature: float = 0.7
    num_ctx: int = 4096
    max_turns: int = 10

    # Prompt settings
    prompt_mode: str = "default"  # "default" or "custom"
    custom_prompt: str = ""

    # Greetings
    wake_greetings: List[str] = field(default_factory=lambda: DEFAULT_GREETINGS.copy())

    # Feature flags
    enable_mcp: bool = False
    enable_web_search: bool = False

    # Tool settings
    tool_cache_size: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentSettings:
        """Create from dictionary, ignoring unknown keys."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def update(self, **kwargs) -> None:
        """Update settings from keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown setting: {key}")


class SettingsManager:
    """Manages loading and saving agent settings."""

    _instance: Optional[SettingsManager] = None

    def __new__(cls) -> SettingsManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = AgentSettings()
            cls._instance._load()
        return cls._instance

    @classmethod
    def get_instance(cls) -> SettingsManager:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def settings(self) -> AgentSettings:
        """Get current settings."""
        return self._settings

    def _load(self) -> None:
        """Load settings from file."""
        if not SETTINGS_FILE.exists():
            logger.info("No settings file found, using defaults")
            return

        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            self._settings = AgentSettings.from_dict(data)
            logger.info(f"Loaded settings from {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def save(self) -> None:
        """Save settings to file."""
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._settings.to_dict(), f, indent=2)
            logger.info(f"Saved settings to {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def update(self, **kwargs) -> AgentSettings:
        """Update and save settings."""
        self._settings.update(**kwargs)
        self.save()
        return self._settings

    def reset(self) -> AgentSettings:
        """Reset to default settings."""
        self._settings = AgentSettings()
        self.save()
        return self._settings

    def get_env_overrides(self) -> Dict[str, Any]:
        """Get settings that should override from environment."""
        overrides = {}

        # Check for environment variable overrides
        env_mapping = {
            "OLLAMA_MODEL": "llm_model",
            "SPEECH_SERVER_TTS_MODEL": "tts_model",
            "SPEECH_SERVER_TTS_VOICE": "tts_voice",
            "SPEECH_SERVER_STT_MODEL": "stt_model",
            "ENABLE_MCP": "enable_mcp",
        }

        for env_key, setting_key in env_mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                if setting_key == "enable_mcp":
                    value = value.lower() in ("1", "true", "yes", "on")
                overrides[setting_key] = value

        return overrides


# Global instance
settings_manager = SettingsManager.get_instance()
