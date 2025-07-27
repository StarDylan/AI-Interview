#!/usr/bin/env python3
"""
WebRTC Transcription Server

A modular WebRTC server that provides real-time audio transcription
with per-session isolation and proper resource management.
"""

import asyncio
import logging
from websockets.asyncio.server import serve as websocket_serve
from pathlib import Path

from config.settings import SERVER_HOST, SERVER_PORT
from handlers.webrtc_handler import WebRTCServer
from utils.ssl_utils import create_ssl_context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('transcription_server.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Start the WebRTC transcription server"""
    logger.info("Starting WebRTC Transcription Server...")
    
    try:
        # Initialize server
        server = WebRTCServer()
        
        # Create SSL context
        ssl_context = create_ssl_context()
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(server.cleanup_inactive_sessions())
        
        logger.info(f"Starting secure WebSocket server on wss://{SERVER_HOST}:{SERVER_PORT}")
        
        # Start WebSocket server
        async with websocket_serve(
            server.handle_client,
            SERVER_HOST,
            SERVER_PORT,
            ssl=ssl_context,
        ):
            logger.info("Server started successfully. Waiting for connections...")
            
            # Log server info
            logger.info("Server features:")
            logger.info("- Per-session audio transcription")
            logger.info("- Session-isolated file storage")
            logger.info("- Real-time WebRTC audio processing")
            logger.info("- Automatic session cleanup")
            
            # Keep server running
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
            finally:
                cleanup_task.cancel()
                logger.info("Server shutdown complete")
    
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        exit(1)