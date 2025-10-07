from typing import Awaitable
from typing import Callable
from typing import TypeVar, Generic, final, runtime_checkable, NewType, Protocol
from dataclasses import dataclass
from ulid import ULID

#
# Resource Key and Types
#

T = TypeVar("T", covariant=True)


@final
@dataclass(frozen=True)
class ResourceKey(Generic[T]):
    """
    A key to access a resource in the context manager.

    Attributes
    ----------
    name:
        unique resource key
    """

    name: str


#
## New Types
#
@dataclass
class UserId:
    _user_id: ULID

    def __str__(self):
        return str(self._user_id).lower()

    @classmethod
    def from_str(cls, user_id: str) -> "UserId":
        return cls(_user_id=ULID.from_str(user_id.upper()))


SessionId = NewType("SessionId", ULID)
ProjectId = NewType("ProjectId", ULID)


@dataclass
class TranscriptId:
    _transcript_id: ULID

    def __str__(self):
        return str(self._transcript_id).lower()

    @classmethod
    def from_str(cls, transcript_id: str) -> "TranscriptId":
        return cls(_transcript_id=ULID.from_str(transcript_id.upper()))


UserIP = NewType("UserIP", str)


@runtime_checkable
class WebSocketProtocol(Protocol):
    async def send_text(self, data: str) -> None: ...
    async def receive_text(self) -> str: ...
    async def close(self) -> None: ...


type AsyncAiProcessor = Callable[["AIJob"], Awaitable[list[AIResult]]]


@dataclass(frozen=True)
class AIJob:
    session_id: SessionId
    up_to_transcript_id: TranscriptId


@dataclass(frozen=True)
class AIResult:
    session_id: SessionId
    text: str
