#!/usr/bin/env python3
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from interview_helper.config import get_settings
from interview_helper.session import SessionManager
from interview_helper.transcription import initialize_vosk_model
from interview_helper.websocket_server import (
    SessionManager as WebSocketSessionManager,
    handle_client,
)
from interview_helper.webrtc_handler import setup_webrtc_hooks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("transcription_server.log")],
)

logger = logging.getLogger(__name__)

# Global managers
session_manager = None
websocket_session_manager = None
cleanup_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global session_manager, websocket_session_manager, cleanup_task

    logger.info("Starting Modular WebRTC Transcription Server...")

    # Initialize Vosk model
    try:
        initialize_vosk_model(
            get_settings().vosk_model_path, get_settings().target_sample_rate
        )
        logger.info("✅ Vosk model initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Vosk model: {e}")
        raise

    # Create session managers
    session_manager = SessionManager()
    websocket_session_manager = WebSocketSessionManager()

    # Setup WebRTC hooks
    webrtc_on_connect, webrtc_on_message, webrtc_on_disconnect = setup_webrtc_hooks(
        session_manager
    )

    # Wire hooks to WebSocket session manager
    websocket_session_manager.set_hooks(
        on_connect=webrtc_on_connect,
        on_message=webrtc_on_message,
        on_disconnect=webrtc_on_disconnect,
    )

    # Start cleanup tasks
    session_manager.start_cleanup_task()
    cleanup_task = asyncio.create_task(_periodic_health_check())

    logger.info("🚀 Server features:")
    logger.info("   - Modular functional architecture")
    logger.info("   - Per-session audio transcription")
    logger.info("   - Hook-based WebRTC handling")
    logger.info("   - Real-time text processing")
    logger.info("   - Session-isolated state management")
    logger.info("✅ Server started successfully")

    yield

    # Cleanup on shutdown
    logger.info("🛑 Shutting down server...")

    if session_manager:
        session_manager.stop_cleanup_task()

    if cleanup_task:
        cleanup_task.cancel()

    logger.info("✅ Server shutdown complete")


async def _periodic_health_check():
    """Periodic health check and logging"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes

            session_count = (
                session_manager.get_active_sessions_count() if session_manager else 0
            )
            websocket_count = (
                websocket_session_manager.get_connection_count()
                if websocket_session_manager
                else 0
            )

            logger.info(
                f"💚 Health check - Sessions: {session_count}, WebSockets: {websocket_count}"
            )

        except Exception as e:
            logger.error(f"❌ Health check error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Modular WebRTC Transcription Server",
    description="A refactored FastAPI-based WebRTC server with functional, modular architecture",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    # FIXME: This is due to Pyrefly not being able to handle Generic ParamSpec and Protocol.
    # See https://github.com/facebook/pyrefly/issues/43
    # pyrefly: ignore[bad-argument-type]
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Modular WebRTC Transcription Server is running",
        "version": "2.0.0",
        "architecture": "functional_modular",
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    session_count = (
        session_manager.get_active_sessions_count() if session_manager else 0
    )
    websocket_count = (
        websocket_session_manager.get_connection_count()
        if websocket_session_manager
        else 0
    )

    return {
        "status": "healthy",
        "active_sessions": session_count,
        "websocket_connections": websocket_count,
        "architecture": "functional_modular",
        "components": {
            "session_manager": "initialized" if session_manager else "not_initialized",
            "websocket_manager": "initialized"
            if websocket_session_manager
            else "not_initialized",
            "vosk_model": "loaded",
        },
    }


@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    if not session_manager or not websocket_session_manager:
        return {"error": "Server not fully initialized"}

    return {
        "sessions": {
            "active": session_manager.get_active_sessions_count(),
        },
        "websockets": {
            "connections": websocket_session_manager.get_connection_count(),
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for WebRTC signaling and transcription"""
    if not websocket_session_manager:
        logger.error("WebSocket session manager not initialized")
        await websocket.close(code=1011, reason="Server not ready")
        return

    await handle_client(websocket, websocket_session_manager)


if __name__ == "__main__":
    try:
        uvicorn.run(
            app,
            host=get_settings().server_host,
            port=get_settings().server_port,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        exit(1)
