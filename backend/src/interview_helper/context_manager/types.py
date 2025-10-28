from typing import (
    TypeVar,
    Generic,
    cast,
    final,
    override,
    runtime_checkable,
    NewType,
    Protocol,
)
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
        return cls(_user_id=cast(ULID, ULID.from_str(user_id.upper())))


SessionId = NewType("SessionId", ULID)


@dataclass
class ProjectId:
    _project_id: ULID

    @override
    def __str__(self):
        return str(self._project_id).lower()

    @classmethod
    def from_str(cls, project_id: str) -> "ProjectId":
        return cls(_project_id=cast(ULID, ULID.from_str(project_id.upper())))


@dataclass
class TranscriptId:
    _transcript_id: ULID

    @override
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


@dataclass(frozen=True)
class AIJob:
    project_id: ProjectId


@dataclass(frozen=True)
class AIResult:
    text: list[str]
