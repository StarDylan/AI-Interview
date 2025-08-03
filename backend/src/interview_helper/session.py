import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
import json
import logging
import asyncio

from interview_helper.messages import Message, TranscriptionMessage, ErrorMessage

logger = logging.getLogger(__name__)

SendCallback = Callable[[Message], Awaitable[None]]


@dataclass
class Session:
    """Encapsulates per-user state with minimal state management"""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    send_callback: Optional[SendCallback] = None

    # Session-specific data
    transcription_buffer: list = field(default_factory=list)
    audio_buffer: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_transcription(
        self, text: str, is_partial: bool = False, timestamp: Optional[datetime] = None
    ):
        """Add transcription text to session buffer"""
        if timestamp is None:
            timestamp = datetime.now()

        entry = {
            "text": text,
            "timestamp": timestamp.isoformat(),
            "session_id": self.session_id,
            "is_partial": is_partial,
        }
        self.transcription_buffer.append(entry)
        logger.debug(f"Session {self.session_id[:8]}: Added transcription: {text}")

    def get_full_transcription(self) -> str:
        """Get complete transcription text for this session (non-partial only)"""
        return " ".join(
            [
                item["text"]
                for item in self.transcription_buffer
                if not item.get("is_partial", False)
            ]
        )

    def get_transcription_json(self) -> str:
        """Get transcription data as JSON"""
        return json.dumps(
            {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "created_at": self.created_at.isoformat(),
                "transcriptions": self.transcription_buffer,
                "metadata": self.metadata,
            },
            indent=2,
        )

    async def send_transcription(self, text: str, is_partial: bool = False):
        """Send transcription message"""
        message = TranscriptionMessage(
            session_id=self.session_id, text=text, is_partial=is_partial
        )
        await self.send(message)

    async def send_error(self, error_code: str, error_message: str):
        """Send error message"""
        message = ErrorMessage(
            error_code=error_code, message=error_message, session_id=self.session_id
        )
        await self.send(message)

    async def send(self, message: Message):
        """Send message via callback if available"""
        if self.send_callback:
            await self.send_callback(message)
        else:
            logger.warning(f"Session {self.session_id[:8]}: No send callback available")

    def deactivate(self):
        """Mark session as inactive"""
        self.is_active = False
        logger.info(f"Session {self.session_id[:8]}: Deactivated")


class SessionManager:
    """Manages active sessions and routes audio chunks"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info("SessionManager initialized")

    def create_session(self, user_id: str, send_callback: SendCallback) -> Session:
        """Create new session for user"""
        session = Session(user_id=user_id, send_callback=send_callback)
        self.sessions[session.session_id] = session
        logger.info(f"Created session {session.session_id[:8]} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_session_by_user(self, user_id: str) -> Optional[Session]:
        """Get active session for user"""
        for session in self.sessions.values():
            if session.user_id == user_id and session.is_active:
                return session
        return None

    def remove_session(self, session_id: str) -> bool:
        """Remove session by ID"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.deactivate()
            del self.sessions[session_id]
            logger.info(f"Removed session {session_id[:8]}")
            return True
        return False

    def route_audio_chunk(self, user_id: str, chunk: bytes) -> Optional[Session]:
        """Route audio chunk to user's active session"""
        session = self.get_session_by_user(user_id)
        if session and session.is_active:
            session.audio_buffer.append(chunk)
            logger.debug(f"Routed audio chunk to session {session.session_id[:8]}")
            return session
        else:
            logger.warning(f"No active session found for user {user_id}")
            return None

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return sum(1 for session in self.sessions.values() if session.is_active)

    def cleanup_inactive_sessions(self):
        """Remove inactive sessions"""
        inactive_sessions = [
            session_id
            for session_id, session in self.sessions.items()
            if not session.is_active
        ]

        for session_id in inactive_sessions:
            del self.sessions[session_id]

        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")

    def start_cleanup_task(self, interval: int = 60):
        """Start periodic cleanup task"""

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    self.cleanup_inactive_sessions()
                except Exception as e:
                    logger.error(f"Error during session cleanup: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started cleanup task with {interval}s interval")

    def stop_cleanup_task(self):
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            logger.info("Stopped cleanup task")
