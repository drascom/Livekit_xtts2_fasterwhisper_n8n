"""Runtime settings management for CAAL voice agent.

Settings persist to a JSON file and are loaded at session start.
Some settings are hot-swappable mid-session.

Settings hierarchy:
1. settings.json - Runtime-configurable values
2. .env - Infrastructure values (URLs, tokens) - fallback only

Prompt files:
- system-prompt.md - Ships with voice-agent, read-only in UI
- prompt/custom.md - User's custom prompt (gitignored)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Paths - use environment variable for Docker, fallback for local dev
_SCRIPT_DIR = Path(__file__).parent
SETTINGS_PATH = Path(os.getenv("CAAL_SETTINGS_PATH", _SCRIPT_DIR / "settings.json"))
PROMPT_DIR = Path(os.getenv("CAAL_PROMPT_DIR", _SCRIPT_DIR / "prompt"))
SYSTEM_PROMPT_PATH = Path(
    os.getenv("CAAL_SYSTEM_PROMPT_PATH", _SCRIPT_DIR / "system-prompt.md")
)

DEFAULT_SETTINGS = {
    "agent_name": "Cal",
    "tts_voice": "ayhan",
    "prompt": "default",  # "default" or "custom"
    "wake_greetings": [
        "Hey, what's up?",
        "Hi there!",
        "Yeah?",
        "What can I do for you?",
        "Hey!",
        "Yo!",
        "What's up?",
    ],
    "temperature": 0.7,
    "model": "ministral-3:8b",
    "num_ctx": 8192,
    "max_turns": 20,
    "tool_cache_size": 3,
}

# Cached settings (reloaded on save)
_settings_cache: dict | None = None


def load_settings() -> dict:
    """Load settings from JSON file, merged with defaults.

    Returns:
        Settings dict with all keys from DEFAULT_SETTINGS,
        overridden by values from settings.json if present.
    """
    global _settings_cache

    if _settings_cache is not None:
        return _settings_cache

    settings = DEFAULT_SETTINGS.copy()

    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                user_settings = json.load(f)
            # Only apply keys that exist in defaults (ignore unknown keys)
            for key in DEFAULT_SETTINGS:
                if key in user_settings:
                    settings[key] = user_settings[key]
            logger.debug(f"Loaded settings from {SETTINGS_PATH}")
        except Exception as e:
            logger.warning(f"Failed to load settings from {SETTINGS_PATH}: {e}")
    else:
        logger.debug(f"No settings file at {SETTINGS_PATH}, using defaults")

    _settings_cache = settings
    return settings


def save_settings(settings: dict) -> None:
    """Save settings to JSON file.

    Args:
        settings: Settings dict to save. Only keys in DEFAULT_SETTINGS are saved.
    """
    global _settings_cache

    # Filter to only known keys
    filtered = {k: v for k, v in settings.items() if k in DEFAULT_SETTINGS}

    try:
        # Ensure parent directory exists
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(SETTINGS_PATH, "w") as f:
            json.dump(filtered, f, indent=2)

        # Invalidate cache
        _settings_cache = None

        logger.info(f"Saved settings to {SETTINGS_PATH}")
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value.

    Args:
        key: Setting key name
        default: Fallback if key not found (defaults to value from DEFAULT_SETTINGS)

    Returns:
        Setting value
    """
    settings = load_settings()
    if default is None:
        default = DEFAULT_SETTINGS.get(key)
    return settings.get(key, default)


def reload_settings() -> dict:
    """Force reload settings from disk.

    Returns:
        Fresh settings dict
    """
    global _settings_cache
    _settings_cache = None
    return load_settings()


# =============================================================================
# Prompt File Management
# =============================================================================


def get_prompt_path(prompt_name: str) -> Path:
    """Get path to a prompt file.

    Args:
        prompt_name: "default" or "custom"

    Returns:
        Path to the prompt .md file
    """
    if prompt_name == "default":
        return SYSTEM_PROMPT_PATH
    return PROMPT_DIR / f"{prompt_name}.md"


def load_prompt_content(prompt_name: str | None = None) -> str:
    """Load raw prompt content from file.

    Args:
        prompt_name: "default" or "custom". If None, uses settings["prompt"].

    Returns:
        Prompt file content, or default content if file doesn't exist.
    """
    if prompt_name is None:
        prompt_name = get_setting("prompt", "default")

    prompt_path = get_prompt_path(prompt_name)

    # If custom doesn't exist, fall back to default
    if prompt_name == "custom" and not prompt_path.exists():
        prompt_path = get_prompt_path("default")

    try:
        return prompt_path.read_text()
    except Exception as e:
        logger.error(f"Failed to load prompt from {prompt_path}: {e}")
        return ""


def save_custom_prompt(content: str) -> None:
    """Save content to prompt/custom.md.

    Args:
        content: Prompt content to save
    """
    prompt_path = get_prompt_path("custom")

    try:
        PROMPT_DIR.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(content)
        logger.info(f"Saved custom prompt to {prompt_path}")
    except Exception as e:
        logger.error(f"Failed to save custom prompt: {e}")
        raise


def load_prompt_with_context(
    timezone_id: str = "America/Los_Angeles",
    timezone_display: str = "Pacific Time",
) -> str:
    """Load prompt and populate with date/time context.

    This is the main function used by voice_agent.py to get the
    fully-populated system prompt.

    Args:
        timezone_id: IANA timezone ID for current time
        timezone_display: Human-readable timezone name

    Returns:
        Prompt with {{CURRENT_DATE_CONTEXT}} and {{TIMEZONE}} replaced
    """
    from utils.formatting import (
        format_date_speech_friendly,
        format_time_speech_friendly,
    )

    template = load_prompt_content()

    now = datetime.now(ZoneInfo(timezone_id))
    date_context = (
        f"Today is {format_date_speech_friendly(now)}. "
        f"The current time is {format_time_speech_friendly(now)} {timezone_display}."
    )

    prompt = template.replace("{{CURRENT_DATE_CONTEXT}}", date_context)
    prompt = prompt.replace("{{TIMEZONE}}", timezone_display)

    return prompt


def custom_prompt_exists() -> bool:
    """Check if a custom prompt file exists."""
    return get_prompt_path("custom").exists()
