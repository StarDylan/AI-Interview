from datetime import datetime
from typing import Optional, Dict, Any, Literal, Annotated, Union

from pydantic import BaseModel, Field

# WARNING: When adding new message types,
# be sure that type is unique across all message types.


class TranscriptionMessage(BaseModel):
    type: Literal["transcription"] = "transcription"
    timestamp: datetime = Field(default_factory=datetime.now)
    text: str


class AIResultMessage(BaseModel):
    type: Literal["ai_result"] = "ai_result"
    timestamp: datetime = Field(default_factory=datetime.now)
    text: str


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


class PingMessage(BaseModel):
    type: Literal["ping"] | Literal["pong"] = "pong"
    timestamp: datetime = Field(default_factory=datetime.now)


class CatchupMessage(BaseModel):
    type: Literal["catchup"] = "catchup"
    timestamp: datetime = Field(default_factory=datetime.now)
    transcript: str
    insights: list[str]


class ProjectMetadataMessage(BaseModel):
    type: Literal["project_metadata"] = "project_metadata"
    timestamp: datetime = Field(default_factory=datetime.now)
    project_id: str
    project_name: str


WebSocketMessage = Union[
    ErrorMessage,
    TranscriptionMessage,
    WebRTCMessage,
    PingMessage,
    AIResultMessage,
    CatchupMessage,
    ProjectMetadataMessage,
]


class Envelope(BaseModel):
    message: Annotated[
        WebSocketMessage,
        Field(discriminator="type"),
    ]
