"""Global session registry for webhook access to active agent sessions.

This module provides a way to access running AgentSession instances from
external HTTP endpoints (webhooks). Sessions are registered when they start
and unregistered when they end.

Usage:
    # In entrypoint(), after session.start():
    from caal import session_registry
    session_registry.register(ctx.room.name, session, assistant)

    # In webhook endpoint:
    result = session_registry.get("voice_assistant_room")
    if result:
        session, agent = result
        await session.say("Hello!")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from livekit.agents import AgentSession

logger = logging.getLogger(__name__)

# Global registry: room_name -> (session, agent)
_sessions: dict[str, tuple[Any, Any]] = {}


def register(room_name: str, session: "AgentSession", agent: Any) -> None:
    """Register an active session for webhook access.

    Args:
        room_name: The LiveKit room name (e.g. "voice_assistant_room")
        session: The AgentSession instance
        agent: The VoiceAssistant agent instance
    """
    _sessions[room_name] = (session, agent)
    logger.debug(f"Session registered for room: {room_name}")


def unregister(room_name: str) -> None:
    """Unregister a session when it ends.

    Args:
        room_name: The LiveKit room name
    """
    if room_name in _sessions:
        _sessions.pop(room_name)
        logger.info(f"Session unregistered for room: {room_name}")


def get(room_name: str) -> tuple[Any, Any] | None:
    """Get an active session by room name.

    Args:
        room_name: The LiveKit room name

    Returns:
        Tuple of (AgentSession, VoiceAssistant) if found, None otherwise
    """
    return _sessions.get(room_name)


def list_rooms() -> list[str]:
    """List all rooms with active sessions.

    Returns:
        List of room names with registered sessions
    """
    return list(_sessions.keys())
