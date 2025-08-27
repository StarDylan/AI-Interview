#!/usr/bin/env python3
from starlette.responses import JSONResponse
from fastapi.exceptions import HTTPException
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
from fastapi import FastAPI, WebSocket, Depends, status
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
CLIENT_ID = "7i45dh6u7tt5lnpq3c8sjus39p"
CLIENT_SECRET = "1os3k33evdio00scb6ts7m0r2nrss4q2se5n1jj0fpttedld8r2a"
SITE_URL = "http://localhost:3000"
REDIRECT_URI = f"{SITE_URL}/auth/callback"
SCOPE = "openid profile email"

FRONTEND_REDIRECT_URI = "http://localhost:3000/auth/callback"

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


@app.get("/auth/callback")
async def auth_callback(code: str, state: str):
    """
    This is the callback endpoint where the IdP redirects the user.
    The backend exchanges the code for tokens and returns them to the frontend.
    """
    if state not in active_states or active_states[state][0] != "valid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter."
        )
    del active_states[state]

    # Exchange the authorization code for tokens (server-to-server)
    async with httpx.AsyncClient() as client:
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        try:
            response = await client.post(TOKEN_ENDPOINT, data=token_data)
            response.raise_for_status()
            tokens = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for tokens: {e.response.text}",
            )

    active_states[state] = ("tokens_received", tokens)

    # Step 6: Redirect the user back to the frontend with the state parameter
    redirect_url = f"{FRONTEND_REDIRECT_URI}?state={state}"
    return RedirectResponse(redirect_url)
    # Return the tokens directly to the frontend.
    # The frontend will now store these tokens and handle subsequent authentication.
    return JSONResponse(
        content={
            "access_token": tokens.get("access_token"),
            "id_token": tokens.get("id_token"),
            "token_type": tokens.get("token_type"),
            "expires_in": tokens.get("expires_in"),
            "scope": tokens.get("scope"),
            "refresh_token": tokens.get("refresh_token", None),  # Optional
        }
    )


@app.get("/secured")
async def secured(token: Annotated[str, Depends(oidc_scheme)]):
    print(token)
    verify_jwt_token(
        token.removeprefix("Bearer "), jwks_client, CLIENT_ID, signing_algos
    )
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
