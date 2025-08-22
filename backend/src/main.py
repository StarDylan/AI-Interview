#!/usr/bin/env python3
from interview_helper.audio_stream_handler.audio_utils import (
    async_audio_write_to_disk_consumer_pair,
)
import logging

from interview_helper.config import Settings
from interview_helper.context_manager.messages import WebRTCMessage
from interview_helper.context_manager.session_context_manager import AppContextManager
from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.resource_keys import WEBSOCKET
from interview_helper.audio_stream_handler.audio_stream_handler import (
    handle_webrtc_message,
)

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("transcription_server.log")],
)

logger = logging.getLogger(__name__)

session_manager = AppContextManager(
    (async_audio_write_to_disk_consumer_pair,), settings=Settings()
)

# Create FastAPI app
app = FastAPI(
    title="Modular WebRTC Transcription Server",
    description="A refactored FastAPI-based WebRTC server with functional, modular architecture",
    version="2.0.0",
)

app.add_middleware(
    # FIXME: This is due to Pyrefly not being able to handle Generic ParamSpec and Protocol.
    # See https://github.com/facebook/pyrefly/issues/43
    # pyrefly: ignore[bad-argument-type]
    CORSMiddleware,
    allow_origins=session_manager.get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return "Interview Helper Backend"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # TODO: Authentication
    await websocket.accept()
    context = await session_manager.new_session()

    cws = ConcurrentWebSocket(already_accepted_ws=websocket)

    async with cws:
        await context.register(WEBSOCKET, cws)

        while True:
            message = await cws.receive_message()

            if isinstance(message, WebRTCMessage):
                await handle_webrtc_message(context, message)
            # handle other message types...


if __name__ == "__main__":
    try:
        uvicorn.run(
            app,
            host=session_manager.get_settings().server_host,
            port=session_manager.get_settings().server_port,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        exit(1)
