from datetime import datetime
from typing import Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


class TranscriptionMessage(BaseModel):
    """Real-time transcription update message"""

    type: Literal["transcription"] = "transcription"
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    text: str
    is_partial: bool = False


class ErrorMessage(BaseModel):
    """Error message"""

    type: Literal["error"] = "error"
    timestamp: datetime = Field(default_factory=datetime.now)
    error_code: str
    message: str
    session_id: Optional[str] = None


class WebRTCMessage(BaseModel):
    """WebRTC signaling messages"""

    type: Literal["offer", "answer", "ice_candidate"]
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: Optional[str] = None
    data: Dict[str, Any]


Message = Union[TranscriptionMessage, ErrorMessage, WebRTCMessage]
