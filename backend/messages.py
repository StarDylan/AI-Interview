from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message structure for all WebSocket communications"""

    type: str
    timestamp: datetime = Field(default_factory=datetime.now)


class TranscriptionMessage(BaseMessage):
    """Real-time transcription update message"""

    type: Literal["transcription"] = "transcription"
    session_id: str
    text: str
    is_partial: bool = False


class ErrorMessage(BaseMessage):
    """Error message"""

    type: Literal["error"] = "error"
    error_code: str
    message: str
    session_id: Optional[str] = None


class WebRTCMessage(BaseMessage):
    """WebRTC signaling messages"""

    type: Literal["offer", "answer", "ice_candidate"] = Field(...)
    session_id: Optional[str] = None
    data: Dict[str, Any]
