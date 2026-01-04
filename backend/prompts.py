"""Prompt management for voice agent.

Loads prompts and greetings from prompt.json with date/time context injection.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent / "prompt.json"

# Cache for loaded prompt data
_prompt_cache: Dict[str, Any] | None = None


def _load_prompt_file() -> Dict[str, Any]:
    """Load prompt.json file, with caching."""
    global _prompt_cache

    if _prompt_cache is not None:
        return _prompt_cache

    if not PROMPT_FILE.exists():
        logger.warning(f"Prompt file not found: {PROMPT_FILE}")
        return {}

    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            _prompt_cache = json.load(f)
        logger.debug(f"Loaded prompt from {PROMPT_FILE}")
        return _prompt_cache
    except Exception as e:
        logger.error(f"Failed to load prompt file: {e}")
        return {}


def reload_prompts() -> Dict[str, Any]:
    """Force reload prompts from disk."""
    global _prompt_cache
    _prompt_cache = None
    return _load_prompt_file()


def get_prompt_data() -> Dict[str, Any]:
    """Get the full prompt data dictionary."""
    return _load_prompt_file()


def get_agent_name() -> str:
    """Get the agent's name."""
    data = _load_prompt_file()
    return data.get("agent_name", "Assistant")


def get_wake_greetings() -> List[str]:
    """Get list of wake/greeting phrases."""
    data = _load_prompt_file()
    return data.get("wake_greetings", ["Hello! How can I help you?"])


def get_random_greeting() -> str:
    """Get a random greeting from the list."""
    greetings = get_wake_greetings()
    return random.choice(greetings)


def get_timezone_config() -> Dict[str, str]:
    """Get timezone configuration."""
    data = _load_prompt_file()
    return data.get("timezone", {"id": "UTC", "display": "UTC"})


def format_date_speech_friendly(dt: datetime) -> str:
    """Format date for TTS (e.g., 'Saturday, January fourth, twenty twenty-six')."""
    day = dt.day
    # Ordinal suffix
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    return dt.strftime(f"%A, %B {day}{suffix}, %Y")


def format_time_speech_friendly(dt: datetime) -> str:
    """Format time for TTS (e.g., 'three forty-five PM')."""
    hour = dt.hour
    minute = dt.minute
    period = "AM" if hour < 12 else "PM"

    # Convert to 12-hour format
    if hour == 0:
        hour = 12
    elif hour > 12:
        hour -= 12

    if minute == 0:
        return f"{hour} {period}"
    else:
        return f"{hour}:{minute:02d} {period}"


def get_current_date_context() -> str:
    """Generate current date/time context string for prompt injection."""
    tz_config = get_timezone_config()
    tz_id = tz_config.get("id", "UTC")
    tz_display = tz_config.get("display", "UTC")

    try:
        now = datetime.now(ZoneInfo(tz_id))
    except Exception:
        now = datetime.now()

    date_str = format_date_speech_friendly(now)
    time_str = format_time_speech_friendly(now)

    return f"Today is {date_str}. The current time is {time_str} {tz_display}."


def get_system_prompt(user_name: Optional[str] = None) -> str:
    """Get the system prompt with date/time and user context injected.

    Args:
        user_name: The user's name to personalize the conversation.
    """
    data = _load_prompt_file()
    template = data.get("system_prompt", "You are a helpful voice assistant.")

    # Inject current date context
    date_context = get_current_date_context()
    prompt = template.replace("{{CURRENT_DATE_CONTEXT}}", date_context)

    # Inject user context
    if user_name and user_name.lower() not in ("user", "unknown"):
        user_context = f"You are speaking with {user_name}. Use their name occasionally to make the conversation more personal."
    else:
        user_context = ""
    prompt = prompt.replace("{{USER_CONTEXT}}", user_context)

    return prompt


def get_session_instruction() -> str:
    """Get the session start instruction."""
    data = _load_prompt_file()
    return data.get(
        "session_instruction",
        "Say a brief, friendly greeting."
    )


# For backward compatibility - use functions instead for dynamic content
# AGENT_INSTRUCTION and SESSION_INSTRUCTION are deprecated
# Use get_system_prompt(user_name) and get_session_instruction() instead
