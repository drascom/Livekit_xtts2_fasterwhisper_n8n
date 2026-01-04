"""Session registry for managing multiple concurrent voice agent sessions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Information about an active session."""
    room_name: str
    user_identity: str
    user_name: str
    created_at: datetime = field(default_factory=datetime.now)
    agent_session: Any = None  # AgentSession instance
    agent: Any = None  # Agent instance
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


class SessionRegistry:
    """
    Global registry for tracking active voice agent sessions.
    Enables multi-room support with isolated sessions per user.
    """

    _instance: Optional[SessionRegistry] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> SessionRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions: Dict[str, SessionInfo] = {}
            cls._instance._room_lock = asyncio.Lock()
            cls._instance._greeting_times: Dict[str, datetime] = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> SessionRegistry:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def register(
        self,
        room_name: str,
        user_identity: str,
        user_name: str,
        agent_session: Any = None,
        agent: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionInfo:
        """Register a new session."""
        async with self._room_lock:
            session = SessionInfo(
                room_name=room_name,
                user_identity=user_identity,
                user_name=user_name,
                agent_session=agent_session,
                agent=agent,
                metadata=metadata or {},
            )
            self._sessions[room_name] = session
            logger.info(f"Registered session for room '{room_name}' (user: {user_name})")
            return session

    async def unregister(self, room_name: str) -> Optional[SessionInfo]:
        """Unregister a session by room name."""
        async with self._room_lock:
            session = self._sessions.pop(room_name, None)
            if session:
                logger.info(
                    f"Unregistered session for room '{room_name}' "
                    f"(duration: {session.duration_seconds:.1f}s)"
                )
            return session

    def get(self, room_name: str) -> Optional[SessionInfo]:
        """Get session info by room name."""
        return self._sessions.get(room_name)

    def get_by_user(self, user_identity: str) -> Optional[SessionInfo]:
        """Get session info by user identity."""
        for session in self._sessions.values():
            if session.user_identity == user_identity:
                return session
        return None

    def list_sessions(self) -> list[SessionInfo]:
        """List all active sessions."""
        return list(self._sessions.values())

    @property
    def active_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._sessions)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state for API responses."""
        return {
            "active_sessions": self.active_count,
            "sessions": [
                {
                    "room_name": s.room_name,
                    "user_identity": s.user_identity,
                    "user_name": s.user_name,
                    "created_at": s.created_at.isoformat(),
                    "duration_seconds": s.duration_seconds,
                    "metadata": s.metadata,
                }
                for s in self._sessions.values()
            ],
        }

    def should_greet(self, user_identity: str, min_seconds: int = 3600) -> bool:
        """Return True if a greeting should be sent for this user."""
        last_greeted_at = self._greeting_times.get(user_identity)
        if last_greeted_at is None:
            return True
        return (datetime.now() - last_greeted_at).total_seconds() >= min_seconds

    def record_greeting(self, user_identity: str) -> None:
        """Record that a greeting was sent for this user."""
        self._greeting_times[user_identity] = datetime.now()


# Global instance
registry = SessionRegistry.get_instance()
