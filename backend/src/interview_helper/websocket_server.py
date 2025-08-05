import asyncio
import logging
from typing import Dict, Callable, Awaitable, Optional
from fastapi import WebSocketDisconnect
from typing import Protocol, runtime_checkable
from interview_helper.messages import Message

logger = logging.getLogger(__name__)

# Hook type definitions
OnConnectHook = Callable[[str, Callable[[Message], Awaitable[None]]], Awaitable[None]]
OnMessageHook = Callable[[str, str], Awaitable[None]]
OnDisconnectHook = Callable[[str], Awaitable[None]]


@runtime_checkable
class WebSocketProtocol(Protocol):
    """The async WebSocket interface your SessionManager/handle_client actually uses."""

    async def accept(self) -> None: ...
    async def send_text(self, text: str) -> None: ...
    async def receive_text(self) -> str: ...


class SessionManager:
    """Encapsulates WebSocket session state and hooks"""

    def __init__(self):
        self._connections: Dict[str, WebSocketProtocol] = {}
        self._lock = asyncio.Lock()
        self._on_connect: Optional[OnConnectHook] = None
        self._on_message: Optional[OnMessageHook] = None
        self._on_disconnect: Optional[OnDisconnectHook] = None

    def set_hooks(
        self,
        on_connect: Optional[OnConnectHook] = None,
        on_message: Optional[OnMessageHook] = None,
        on_disconnect: Optional[OnDisconnectHook] = None,
    ):
        """Set hook functions"""
        self._on_connect = on_connect
        self._on_message = on_message
        self._on_disconnect = on_disconnect

    async def add_connection(self, user_id: str, websocket: WebSocketProtocol):
        """Add connection to manager"""
        async with self._lock:
            self._connections[user_id] = websocket

    async def remove_connection(self, user_id: str):
        """Remove connection from manager"""
        async with self._lock:
            self._connections.pop(user_id)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self._connections)

    # Hook accessors
    @property
    def on_connect(self) -> Optional[OnConnectHook]:
        return self._on_connect

    @property
    def on_message(self) -> Optional[OnMessageHook]:
        return self._on_message

    @property
    def on_disconnect(self) -> Optional[OnDisconnectHook]:
        return self._on_disconnect


async def handle_client(websocket: WebSocketProtocol, session_manager: SessionManager):
    """
    Handle WebSocket client connection - pure function driven by dependency injection
    """
    await websocket.accept()

    # Generate user ID (in real app, this might come from auth)
    user_id: str = f"user_{id(websocket)}"
    await session_manager.add_connection(user_id, websocket)

    logger.info(f"WebSocket client connected: {user_id}")

    # Create send callback for this connection
    async def send_func(message: Message):
        await websocket.send_text(message.model_dump_json())

    try:
        # Call on_connect hook
        if session_manager.on_connect:
            await session_manager.on_connect(user_id, send_func)

        # Handle messages
        while True:
            try:
                message = await websocket.receive_text()

                # Call on_message hook
                if session_manager.on_message:
                    await session_manager.on_message(user_id, message)

            except WebSocketDisconnect:
                break

    finally:
        # Cleanup
        await session_manager.remove_connection(user_id)

        # Call on_disconnect hook
        if session_manager.on_disconnect:
            await session_manager.on_disconnect(user_id)

        logger.info(f"WebSocket client disconnected: {user_id}")
