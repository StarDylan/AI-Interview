from starlette.websockets import WebSocketDisconnect
import pytest
import asyncio
from interview_helper.websocket_server import SessionManager, handle_client
from interview_helper.messages import TranscriptionMessage


# --- Fakes ---
class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self._incoming = asyncio.Queue()

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        assert self.accepted, "Must accept before sending"
        self.sent_messages.append(text)

    async def receive_text(self):
        result = await self._incoming.get()
        if isinstance(result, WebSocketDisconnect):
            raise result
        return result

    def enqueue(self, message):
        """Enqueue a message or exception for receive_text to pop."""
        self._incoming.put_nowait(message)


# --- Fixtures ---
@pytest.fixture
def fake_websocket():
    return FakeWebSocket()


@pytest.fixture
def session_manager():
    return SessionManager()


# --- SessionManager core behavior ---
@pytest.mark.asyncio
async def test_add_and_remove_connection(session_manager: SessionManager):
    ws = FakeWebSocket()
    await session_manager.add_connection("user1", ws)
    assert session_manager.get_connection_count() == 1

    await session_manager.remove_connection("user1")
    assert session_manager.get_connection_count() == 0


# Edge-case: removing non-existent user should raise KeyError
@pytest.mark.asyncio
async def test_remove_nonexistent_connection_raises_key_error(
    session_manager: SessionManager,
):
    with pytest.raises(KeyError):
        await session_manager.remove_connection("no_such_user")


@pytest.mark.asyncio
async def test_handle_client_connection_lifecycle_and_hook_calling(
    fake_websocket: FakeWebSocket, session_manager: SessionManager
):
    messages_received = []

    async def mock_on_connect(user_id, send_func):
        # send a transcription message
        msg = TranscriptionMessage(
            session_id=user_id, text="Hello from server", is_partial=False
        )
        await send_func(msg)

    async def mock_on_message(user_id, message):
        messages_received.append((user_id, message))

    async def mock_on_disconnect(user_id):
        messages_received.append(("disconnect", user_id))

    session_manager.set_hooks(
        on_connect=mock_on_connect,
        on_message=mock_on_message,
        on_disconnect=mock_on_disconnect,
    )

    # Enqueue one user message then trigger disconnect
    fake_websocket.enqueue("test message")
    fake_websocket.enqueue(WebSocketDisconnect())

    await handle_client(fake_websocket, session_manager)

    # verify accept was called
    assert fake_websocket.accepted

    # verify server->client (from our on_connect hook)
    assert len(fake_websocket.sent_messages) == 1
    sent = TranscriptionMessage.model_validate_json(fake_websocket.sent_messages[0])
    assert sent.text == "Hello from server"
    assert sent.is_partial is False

    # verify client->server
    assert messages_received == [
        (sent.session_id, "test message"),
        ("disconnect", sent.session_id),
    ]


@pytest.mark.asyncio
async def test_multiple_connections(session_manager: SessionManager):
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await session_manager.add_connection("user1", ws1)
    await session_manager.add_connection("user2", ws2)
    assert session_manager.get_connection_count() == 2

    await session_manager.remove_connection("user1")
    assert session_manager.get_connection_count() == 1

    await session_manager.remove_connection("user2")
    assert session_manager.get_connection_count() == 0
