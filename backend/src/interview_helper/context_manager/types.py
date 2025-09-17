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

UserId = NewType("UserId", ULID)
SessionId = NewType("SessionId", ULID)
ProjectId = NewType("ProjectId", ULID)
UserIP = NewType("UserIP", str)


@runtime_checkable
class WebSocketProtocol(Protocol):
    async def send_text(self, data: str) -> None: ...
    async def receive_text(self) -> str: ...
    async def close(self) -> None: ...
