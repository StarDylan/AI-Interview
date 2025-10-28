from interview_helper.context_manager.messages import AIResultMessage
from interview_helper.context_manager.resource_keys import WEBSOCKET
from interview_helper.context_manager.types import AIResult, TranscriptId
from interview_helper.context_manager.types import AIJob
from interview_helper.context_manager.TextCoalescer import TextCoalescer
from interview_helper.security.tickets import TicketStore
from typing import Optional, Protocol, Type, runtime_checkable
from collections import defaultdict
from dataclasses import dataclass
from ulid import ULID
from typing import cast, TypeVar, Callable, Awaitable
import anyio
import anyio.abc
import anyio.streams.memory
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
import logging

T = TypeVar("T", covariant=True)
U = TypeVar("U", covariant=True)

type AsyncAudioConsumer = Callable[["SessionContext", "AudioChunk"], Awaitable[None]]
type AsyncAudioConsumerFinalize = Callable[["SessionContext"], Awaitable[None]]


@runtime_checkable
class AIAnalyzer(Protocol):
    def __init__(self, config: Settings, db: PersistentDatabase): ...
    async def analyze(self, job: AIJob) -> AIResult: ...


logger = logging.getLogger(__name__)


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

    def is_active(self) -> bool:
        return self.session_id in self.manager.active_sessions

    async def ingest_audio(self, audio_chunk: AudioChunk):
        await self.manager.ingest_audio(
            session_id=self.session_id, audio_chunk=audio_chunk
        )

    async def teardown(self):
        await self.manager.teardown_session(self.session_id)

    async def accept_transcript(self, new_text: str, transcript_id: TranscriptId):
        await self.manager.accept_transcript(
            self.session_id, text=new_text, transcript_id=transcript_id
        )

    def get_user_id(self):
        return self.manager.session_data[self.session_id].user


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
        ai_processer: Type[AIAnalyzer],
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

        # Track active audio sessions
        self.active_audio_sessions: set[SessionId] = set()
        self.cleanup_waiting_event: dict[SessionId, anyio.Event] = defaultdict(
            anyio.Event
        )

        self.active_ai_analysis: dict[SessionId, anyio.Lock] = defaultdict(anyio.Lock)

        # Static for duration of this context, doesn't require lock.
        self.audio_ingest_consumers = audio_ingest_consumers
        self.settings = settings
        self.ticket_store = TicketStore()

        self.db = PersistentDatabase()

        if settings:
            self.ai_processer: None | AIAnalyzer = ai_processer(settings, self.db)

        # Background Serivces (e.g., to fetch AI results)
        self._background_tg: anyio.abc.TaskGroup | None = None

        self._job_send: anyio.abc.ObjectSendStream[AIJob] | None = None
        self._job_recv: anyio.abc.ObjectReceiveStream[AIJob] | None = None
        self._workers_started = False
        self.text_coalescer: dict[SessionId, TextCoalescer] = {}

    async def new_session(self, user_id: UserId) -> SessionContext:
        session_id = SessionId(ULID())

        async with self.lock:
            # FIXME: Right now we treat every user on the same project.
            self.session_data[session_id] = AppContextManager.SessionData(
                project=GLOBAL_PROJECT, user=user_id
            )

            self.session_task_group[
                session_id
            ] = await anyio.create_task_group().__aenter__()

            self.active_sessions.add(session_id)

            if self.ai_processer is not None:
                assert self.settings

                # Setup Infrastructure needed to ping the AI service every once in a while
                coalescer = TextCoalescer(
                    word_threshold=self.settings.process_transcript_every_word_count,
                    seconds=self.settings.process_transcript_every_secs,
                )

                self.text_coalescer[session_id] = coalescer

                async def handler(_transcript_id: TranscriptId) -> None:
                    await self._submit_ai_processing_job(AIJob(session_id=session_id))

                # Run the coalescer in the session’s TaskGroup you already maintain
                tg = self.session_task_group[session_id]
                tg.start_soon(coalescer.run, handler)

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

    async def set_active_audio_session(self, session_id: SessionId):
        async with self.lock:
            self.active_audio_sessions.add(session_id)

    async def clear_active_audio_session(self, session_id: SessionId):
        event = None

        async with self.lock:
            self.active_audio_sessions.remove(session_id)

            if session_id in self.cleanup_waiting_event:
                event = self.cleanup_waiting_event[session_id]

        if event is not None:
            event.set()

    async def teardown_session(self, session_id: SessionId) -> None:
        """Teardown all resources for a websocket session"""

        # Wait for any finishing audio handlers
        event = None
        async with self.lock:
            if session_id in self.active_audio_sessions:
                event = self.cleanup_waiting_event[session_id]

        if event is not None:
            await event.wait()

        async with self.lock:
            for k in self.store_keys[session_id]:
                del self.store[k]

                if k in self.waiting_events:
                    # Notify any waiting events that session is done
                    self.waiting_events[k].set()
                    del self.waiting_events[k]

            del self.store_keys[session_id]

            del self.session_data[session_id]

            self.active_sessions.remove(session_id)

            # Remove from active audio sessions and notify
            if session_id in self.active_audio_sessions:
                self.active_audio_sessions.remove(session_id)
                # Optionally notify any listeners here if needed

            task_group = self.session_task_group[session_id]

            del self.session_task_group[session_id]

        await task_group.__aexit__(None, None, None)

    async def ingest_audio(self, session_id: SessionId, audio_chunk: AudioChunk):
        ctx = SessionContext(self, session_id)
        for consumer, _ in self.audio_ingest_consumers:
            await consumer(ctx, audio_chunk)

    async def accept_transcript(
        self, session_id: SessionId, text: str, transcript_id: TranscriptId
    ):
        async with self.lock:
            assert session_id in self.active_sessions, f"{session_id} is not active!"

            await self.text_coalescer[session_id].push(
                text=text, transcript_id=transcript_id
            )

    async def _submit_ai_processing_job(self, job: AIJob):
        assert self._workers_started
        assert self._job_send is not None

        await self._job_send.send(job)

    async def start_background_services(self, max_buffer_size=5) -> None:
        """
        Creates a global TaskGroup + job queue + worker pool.
        Call this once on app startup (FastAPI lifespan).
        """
        if self._background_tg is not None:
            return  # already started

        if self.ai_processer is None:
            logger.warning(
                "Tried to start background services, but no ai_processor is set!"
            )
            return  # Nothing to start, we didn't provide a processor

        # Long-lived service TG
        self._background_tg = await anyio.create_task_group().__aenter__()

        job_send, job_recv = anyio.create_memory_object_stream[AIJob](
            max_buffer_size=max_buffer_size
        )
        self._job_send = job_send
        self._job_recv = job_recv

        # Spawn workers inside service TG
        for i in range(4):
            self._background_tg.start_soon(
                self._worker, f"bg-w{i}", self._job_recv.clone()
            )

        self._workers_started = True

    async def _worker(
        self, name: str, recv: anyio.abc.ObjectReceiveStream[AIJob]
    ) -> None:
        async with recv:
            # Jobs are simply to "poke" the AI engine that data is incoming.
            # If it is already running that is fine, there will always be another "poke"
            async for job in recv:
                try:
                    if self.active_ai_analysis[job.session_id].locked():
                        continue
                    async with self.active_ai_analysis[job.session_id]:
                        assert self.ai_processer, (
                            "Should never happen since we check this is not None when we start background services"
                        )
                        results = await self.ai_processer.analyze(job)

                    ws = await self.get(job.session_id, WEBSOCKET)
                    if ws:
                        for result in results.text:
                            await ws.send_message(AIResultMessage(text=result))

                except Exception:
                    # Never let an exception kill the worker or the service TG
                    import logging

                    logging.getLogger(__name__).exception(
                        "background worker %s failed processing job: %r", name, job
                    )

    async def stop_background_services(self) -> None:
        """
        Gracefully drains and shuts down the background service.
        """
        if self._background_tg is None:
            return

        # Close send end so workers finish when queue drains
        if self._job_send is not None:
            await self._job_send.aclose()

        # Exit task group (this will wait for workers to exit)
        await self._background_tg.__aexit__(None, None, None)

        # Clear handles
        self._background_tg = None
        self._job_send = None
        self._job_recv = None
