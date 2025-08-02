#!/usr/bin/env python3
"""
FastAPI WebRTC Transcription Server

A FastAPI-based WebRTC server that provides real-time audio transcription
with per-session isolation and proper resource management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import SERVER_HOST, SERVER_PORT
from handlers.webrtc_handler import WebRTCServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("transcription_server.log")],
)

logger = logging.getLogger(__name__)

# Global server instance
webrtc_server = None
cleanup_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global webrtc_server, cleanup_task

    logger.info("Starting WebRTC Transcription Server...")

    # Initialize server
    webrtc_server = WebRTCServer()

    # Start cleanup task
    cleanup_task = asyncio.create_task(webrtc_server.cleanup_inactive_sessions())

    logger.info("Server features:")
    logger.info("- Per-session audio transcription")
    logger.info("- Session-isolated file storage")
    logger.info("- Real-time WebRTC audio processing")
    logger.info("- Automatic session cleanup")
    logger.info("FastAPI server started successfully")

    yield

    # Cleanup on shutdown
    if cleanup_task:
        cleanup_task.cancel()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="WebRTC Transcription Server",
    description="A FastAPI-based WebRTC server for real-time audio transcription",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    # pyrefly: ignore[bad-argument-type]
    # FIX ME: This is a workaround for Pyrefly not handling ParamSpec correctly
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "WebRTC Transcription Server is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    active_sessions = webrtc_server.get_active_sessions_count() if webrtc_server else 0
    return {"status": "healthy", "active_sessions": active_sessions}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for WebRTC signaling"""
    global webrtc_server

    if not webrtc_server:
        logger.error("WebRTC server not initialized")
        await websocket.close(code=1011, reason="Server not ready")
        return

    await websocket.accept()
    logger.info(f"New WebSocket connection: {websocket.client}")

    try:
        # Create a websocket-like wrapper for compatibility
        class WebSocketWrapper:
            def __init__(self, websocket: WebSocket):
                self.websocket = websocket
                self.remote_address = websocket.client

            async def send(self, message: str):
                await self.websocket.send_text(message)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    message = await self.websocket.receive_text()
                    return message
                except WebSocketDisconnect:
                    raise StopAsyncIteration

        # Use the existing WebRTC handler
        wrapper = WebSocketWrapper(websocket)
        await webrtc_server.handle_client(wrapper)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"Error handling WebSocket client: {e}")


if __name__ == "__main__":
    try:
        uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        exit(1)
