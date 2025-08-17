import anyio.abc
from anyio import create_memory_object_stream
from anyio.streams.memory import MemoryObjectReceiveStream
from typing import Optional

from interview_helper.context_manager.types import WebSocketProtocol
from interview_helper.context_manager.messages import Envelope, WebSocketMessage


class ConcurrentWebSocket:
    """
    Concurrency-safe websocket sender for AnyIO.

    - Multiple tasks can call send_* concurrently.
    - Exactly one background task touches ws.send_*.
    - Bounded buffer for backpressure.
    - Clean shutdown (flushes channel, exits writer).

    Usage:
        cws = ConcurrentWebSocket(ws)
        await cws.start()
        await cws.send_message(model)
        await cws.receive_message()
        await cws.aclose()
    """

    def __init__(
        self,
        already_accepted_ws: WebSocketProtocol,
        *,
        message_buffer_size: int = 256,
    ):
        self._ws = already_accepted_ws
        self._send_to_client, self._recv_to_client = create_memory_object_stream[
            WebSocketMessage
        ](message_buffer_size)
        self._task_group: Optional[anyio.abc.TaskGroup] = None
        self._started = False
        self._closed = False

    # ---------- lifecycle ----------
    async def start(self) -> "ConcurrentWebSocket":
        if self._started:
            return self

        # We want to keep this open.
        self._task_group = await anyio.create_task_group().__aenter__()

        self._task_group.start_soon(self._writer, self._recv_to_client, self._ws)
        self._started = True
        return self

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Close the producer side so writer drains & exits
        await self._send_to_client.aclose()

        if self._task_group is not None:
            await self._task_group.__aexit__(None, None, None)
            self._task_group = None

    async def __aenter__(self) -> "ConcurrentWebSocket":
        return await self.start()

    async def __aexit__(self, et, ev, tb) -> None:
        await self.aclose()

    async def _writer(
        self,
        recieve_stream_to_client: MemoryObjectReceiveStream[WebSocketMessage],
        websocket: WebSocketProtocol,
    ) -> None:
        async with recieve_stream_to_client:
            async for msg in recieve_stream_to_client:
                msg_to_send = Envelope(message=msg)
                await websocket.send_text(msg_to_send.model_dump_json())

        await websocket.close()

    async def send_message(self, message: WebSocketMessage) -> None:
        await self._send_to_client.send(message)

    async def receive_message(self) -> WebSocketMessage:
        msg = await self._ws.receive_text()
        recv_msg = Envelope.model_validate_json(msg)
        return recv_msg.message
