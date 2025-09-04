#!/usr/bin/env python3
from starlette.responses import RedirectResponse
from typing import Dict
from interview_helper.security.http import verify_jwt_token
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

# OIDC Configuration - configured via environment variables

OIDC_CONFIG_URL = (
    session_manager.get_settings().oidc_authority.rstrip("/")
    + "/.well-known/openid-configuration"
)
CLIENT_ID = session_manager.get_settings().oidc_client_id
SITE_URL = session_manager.get_settings().site_url
REDIRECT_URI = f"{SITE_URL}/auth/callback"
SCOPE = "openid profile email"

FRONTEND_REDIRECT_URI = session_manager.get_settings().frontend_redirect_uri

oidc_config = httpx.get(OIDC_CONFIG_URL).raise_for_status().json()

signing_algos = oidc_config.get("id_token_signing_alg_values_supported", [])
jwks_client = jwt.PyJWKClient(oidc_config["jwks_uri"])
AUTHORIZATION_ENDPOINT = oidc_config["authorization_endpoint"]
TOKEN_ENDPOINT = oidc_config["token_endpoint"]

oidc_scheme = OpenIdConnect(openIdConnectUrl=OIDC_CONFIG_URL)


@app.get("/")
async def root():
    return "Interview Helper Backend"


active_states: Dict[str, tuple[str, str]] = {}


@app.get("/login")
async def login_redirect():
    """
    Frontend calls this endpoint to initiate the login flow.
    """
    state = "some_random_string_from_the_frontend"  # In a real app, generate a secure random string
    active_states[state] = ("valid", "")

    auth_url = (
        f"{AUTHORIZATION_ENDPOINT}?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope={SCOPE}&"
        f"state={state}"
    )
    return RedirectResponse(auth_url)


@app.get("/auth/token")
async def get_user_token(token: Annotated[str, Depends(oidc_scheme)]):
    """
    Get user information and return a clean token for WebSocket authentication.
    This endpoint verifies the token and returns user claims.
    """
    clean_token = token.removeprefix("Bearer ")
    user_claims = verify_jwt_token(clean_token, jwks_client, CLIENT_ID, signing_algos)

    return {
        "token": clean_token,
        "user": {
            "sub": user_claims.sub,
            "name": user_claims.name,
            "email": user_claims.email,
            "picture": getattr(user_claims, "picture", None),
        },
        "expires_at": user_claims.exp,
    }


@app.get("/secured")
async def secured(token: Annotated[str, Depends(oidc_scheme)]):
    """
    Example secured endpoint that requires authentication.
    """
    user_claims = verify_jwt_token(
        token.removeprefix("Bearer "), jwks_client, CLIENT_ID, signing_algos
    )
    return {
        "message": "Access granted to secured endpoint",
        "user": {
            "sub": user_claims.sub,
            "name": user_claims.name,
            "email": user_claims.email,
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint with authentication.
    Clients should pass the JWT token as a query parameter: /ws?token=<jwt_token>
    """
    # Authenticate the WebSocket connection
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        # Verify the JWT token
        user_claims = verify_jwt_token(token, jwks_client, CLIENT_ID, signing_algos)
        logger.info(f"WebSocket connection authenticated for user: {user_claims.sub}")
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Invalid authentication token")
        return

    await websocket.accept()
    context = await session_manager.new_session()

    cws = ConcurrentWebSocket(already_accepted_ws=websocket)

    async with cws:
        await context.register(WEBSOCKET, cws)

        # Store user information in the session context
        await context.register("user_claims", user_claims)

        while True:
            try:
                message = await cws.receive_message()

                if isinstance(message, WebRTCMessage):
                    await handle_webrtc_message(context, message)
                # handle other message types...
            except Exception as e:
                logger.error(f"WebSocket error for user {user_claims.sub}: {e}")
                break


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
