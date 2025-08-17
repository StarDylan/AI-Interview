from datetime import datetime
from typing import Optional, Dict, Any, Literal, Annotated

from pydantic import BaseModel, Field


class TranscriptionMessage(BaseModel):
    type: Literal["transcription"] = "transcription"
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    text: str
    is_partial: bool = False


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    timestamp: datetime = Field(default_factory=datetime.now)
    error_code: str
    message: str
    session_id: Optional[str] = None


class WebRTCMessage(BaseModel):
    """
    WebRTC signaling messages. Kept loose because lower layers handle details.
    """

    type: Literal["offer", "answer", "ice_candidate"]
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]


WebSocketMessage: type[ErrorMessage | TranscriptionMessage | WebRTCMessage] = (
    TranscriptionMessage | ErrorMessage | WebRTCMessage
)


class Envelope(BaseModel):
    message: Annotated[
        WebSocketMessage,
        Field(discriminator="type"),
    ]
