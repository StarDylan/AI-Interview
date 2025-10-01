from interview_helper.security.tickets import TicketStore
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass
from ulid import ULID
from typing import cast, TypeVar, Callable, Awaitable
import anyio
import anyio.abc
import sys

from interview_helper.config import Settings
from interview_helper.context_manager.types import (
    SessionId,
    ProjectId,
    UserId,
    ResourceKey,
)
from interview_helper.audio_stream_handler.types import AudioChunk
from interview_helper.context_manager.database import PersistentDatabase

T = TypeVar("T", covariant=True)
U = TypeVar("U", covariant=True)

type AsyncAudioConsumer = Callable[["SessionContext", "AudioChunk"], Awaitable[None]]
type AsyncAudioConsumerFinalize = Callable[["SessionContext"], Awaitable[None]]


@dataclass(frozen=True)
class SessionContext:
    manager: "AppContextManager"
    session_id: SessionId

    async def register(self, key: ResourceKey[T], value: T) -> None:
        """
        Registers the resource with the store

        Raises:
            Assertion Error: If resource registered before on this session.
        """

        return await self.manager.register(
            session_id=self.session_id, key=key, value=value
        )

    async def get(self, key: ResourceKey[T]) -> Optional[T]:
        """
        Gets the resource associated with the key

        Raises:
            Assertion Error: If resource not registered already.
        """
        return await self.manager.get(session_id=self.session_id, key=key)

    async def get_or_wait(self, key: ResourceKey[T]):
        return await self.manager.get_or_wait(self.session_id, key)

    def get_settings(self) -> Settings:
        return self.manager.get_settings()

    async def ingest_audio(self, audio_chunk: AudioChunk):
        await self.manager.ingest_audio(
            session_id=self.session_id, audio_chunk=audio_chunk
        )


# FIXME: Remove global project + user
GLOBAL_PROJECT = ProjectId(ULID())
GLOBAL_USER = UserId(ULID())


class AppContextManager:
    """
    Centrally manages all data for the application per-session, per-project, and per-user.
    """

    @dataclass
    class SessionData:
        project: ProjectId
        user: UserId

    def __init__(
        self,
        audio_ingest_consumers: tuple[
            tuple[AsyncAudioConsumer, AsyncAudioConsumerFinalize], ...
        ],
        settings: Settings | None = None,
    ):
        # We need to protect against race-conditions since our context might end up in an
        # inconsistent state between threads.
        self.lock = anyio.Lock()

        self.store: dict[tuple[ResourceKey[object], SessionId], object] = {}
        self.store_keys: dict[
            SessionId, list[tuple[ResourceKey[object], SessionId]]
        ] = defaultdict(list)
        self.waiting_events: dict[
            tuple[ResourceKey[object], SessionId], anyio.Event
        ] = defaultdict(anyio.Event)

        self.session_data: dict[SessionId, AppContextManager.SessionData] = {}
        self.active_sessions = set()

        self.session_task_group: dict[SessionId, anyio.abc.TaskGroup] = {}

        # Static for duration of this context, doesn't require lock.
        self.audio_ingest_consumers = audio_ingest_consumers
        self.settings = settings
        self.ticket_store = TicketStore()

        self.db = PersistentDatabase()

    async def new_session(self) -> SessionContext:
        session_id = SessionId(ULID())

        async with self.lock:
            # FIXME: Right now we treat every user as the same user on the same project.
            self.session_data[session_id] = AppContextManager.SessionData(
                project=GLOBAL_PROJECT, user=GLOBAL_USER
            )

            self.session_task_group[
                session_id
            ] = await anyio.create_task_group().__aenter__()

            self.active_sessions.add(session_id)

        return SessionContext(manager=self, session_id=session_id)

    def get_settings(self) -> Settings:
        # Initing settings causes Env lookups, we make sure that doesn't happen
        assert "pytest" not in sys.modules

        return cast(Settings, self.settings)

    async def register(
        self, session_id: SessionId, key: ResourceKey[T], value: T
    ) -> None:
        """
        Registers the resource with the store

        Raises:
            Assertion Error: If resource registered before on this session.
        """
        k = (key, session_id)

        async with self.lock:
            assert session_id in self.active_sessions, f"{session_id} is not active!"
            assert k not in self.store, (
                f"{key.name} already registered for SessionId({session_id})"
            )

            self.store[k] = value
            self.store_keys[session_id].append(k)

            if k in self.waiting_events:
                self.waiting_events[k].set()

    async def get(self, session_id: SessionId, key: ResourceKey[T]) -> Optional[T]:
        """
        Gets the resource associated with the key

        Raises:
            Assertion Error: If resource not registered already.
        """

        async with self.lock:
            assert session_id in self.active_sessions, f"{session_id} is not active!"

            return cast(T, self.store.get((key, session_id), None))

    async def get_or_wait(self, session_id: SessionId, key: ResourceKey[T]) -> T:
        async with self.lock:
            assert session_id in self.active_sessions, f"{session_id} is not active!"

            potential_value = cast(T | None, self.store.get((key, session_id), None))

            if potential_value is not None:
                return potential_value

            # Get event
            wait_for_value_event = self.waiting_events[(key, session_id)]

        # Wait for value outside of critical section
        await wait_for_value_event.wait()
        async with self.lock:
            return cast(T, self.store[(key, session_id)])

    async def unregister_all(self, session_id: SessionId) -> None:
        """Teardown all resources for a session"""
        async with self.lock:
            for k in self.store_keys[session_id]:
                del self.store[k]

                if k in self.waiting_events:
                    del self.waiting_events[k]

            del self.store_keys[session_id]

            del self.session_data[session_id]

            self.active_sessions.remove(session_id)

            task_group = self.session_task_group[session_id]

            del self.session_task_group[session_id]

        await task_group.__aexit__(None, None, None)

    async def ingest_audio(self, session_id: SessionId, audio_chunk: AudioChunk):
        ctx = SessionContext(self, session_id)
        for consumer, _ in self.audio_ingest_consumers:
            await consumer(ctx, audio_chunk)
