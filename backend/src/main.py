#!/usr/bin/env python3
from interview_helper.security.http import verify_jwt_token
from interview_helper.security.jwks_cache import JWKSCache
from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from typing import cast
from typing import Annotated
from interview_helper.audio_stream_handler.audio_utils import (
    async_audio_write_to_disk_consumer_pair,
)
import logging
import httpx
import jwt

from interview_helper.config import Settings
from interview_helper.context_manager.messages import WebRTCMessage
from interview_helper.context_manager.session_context_manager import AppContextManager
from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.resource_keys import WEBSOCKET
from interview_helper.audio_stream_handler.audio_stream_handler import (
    handle_webrtc_message,
)

from fastapi.security import OpenIdConnect
from fastapi import FastAPI, WebSocket, Depends
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
    # pyrefly: ignore[bad-argument-type]
    CORSMiddleware,
    allow_origins=session_manager.get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Maybe redo with https://github.com/fastapi/fastapi/discussions/10175
# TODO: Configure via ENV Vars
ISSUER = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_WvxLx7BB1/"
OIDC_CONFIG_URL = ISSUER.rstrip("/") + "/.well-known/openid-configuration"
CLIENT_ID="7i45dh6u7tt5lnpq3c8sjus39p"

oidc_config = httpx.get(OIDC_CONFIG_URL).raise_for_status().json()

signing_algos = oidc_config.get("id_token_signing_alg_values_supported", [])
jwks_client = jwt.PyJWKClient(oidc_config["jwks_uri"])

oidc_scheme = OpenIdConnect(openIdConnectUrl=OIDC_CONFIG_URL)

@app.get("/")
async def root():
    return "Interview Helper Backend"

@app.get("/secured")
async def secured(token: Annotated[str, Depends(oidc_scheme)]):
    verify_jwt_token(token, jwks_client, CLIENT_ID, signing_algos)
    return "Secured Endpoint"

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
