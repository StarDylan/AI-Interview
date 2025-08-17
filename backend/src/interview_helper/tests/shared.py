from starlette.websockets import WebSocketDisconnect
from anyio import create_memory_object_stream


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages: list[str] = []
        self.send_stream, self.receive_stream = create_memory_object_stream[str](100)
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, data: str):
        assert self.accepted, "Must accept before sending"
        self.sent_messages.append(data)

    async def receive_text(self):
        result = await self.receive_stream.receive()
        if isinstance(result, WebSocketDisconnect):
            raise result
        return result

    async def close(self):
        self.closed = True

    def enqueue(self, message):
        """Enqueue a message or exception for receive_text to pop."""
        self.send_stream.send_nowait(message)
