#!/usr/bin/env python3
from starlette.websockets import WebSocketDisconnect
from interview_helper.audio_stream_handler.transcriber import transcriber_consumer_pair
from interview_helper.context_manager.messages import PingMessage
from starlette.responses import RedirectResponse
from typing import Dict
from interview_helper.security.http import (
    verify_jwt_token,
    get_user_info_from_oidc_provider,
    get_oidc_userinfo_endpoint,
)
from interview_helper.security.tickets import TicketResponse
from interview_helper.context_manager.types import UserId
from typing import Annotated
from fastapi import Request
from interview_helper.audio_stream_handler.audio_utils import (
    async_audio_write_to_disk_consumer_pair,
)
import logging
import httpx
import jwt
import time
import sqlalchemy as sa
from collections import defaultdict
from typing import DefaultDict

from interview_helper.config import Settings
from interview_helper.context_manager.messages import WebRTCMessage
from interview_helper.context_manager.session_context_manager import AppContextManager
from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.resource_keys import WEBSOCKET
from interview_helper.audio_stream_handler.audio_stream_handler import (
    handle_webrtc_message,
)
from interview_helper.context_manager.database import get_or_add_user

from fastapi.security import OpenIdConnect
from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
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
    # Settings gets initialized from environment variables.
    (async_audio_write_to_disk_consumer_pair, transcriber_consumer_pair),
    # type: ignore[arg-type]
    settings=Settings(),
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

# Rate limiting for ticket generation (per user)
ticket_rate_limit: DefaultDict[str, list] = defaultdict(list)
TICKET_RATE_LIMIT_PER_MINUTE = 10


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


@app.get("/health")
async def health_check():
    """
    Health check endpoint that includes ticket system status.
    """
    return {
        "status": "healthy",
        "service": "Interview Helper Backend",
        "ticket_system": {
            "active_tickets": session_manager.ticket_store.get_active_tickets_count(),
            "default_expiration_seconds": session_manager.ticket_store._default_expiration,
        },
    }


@app.get("/auth/ticket", response_model=TicketResponse)
async def generate_websocket_ticket(
    request: Request, token: Annotated[str, Depends(oidc_scheme)]
):
    """
    Generate an authentication ticket for WebSocket connections.

    This endpoint requires a valid JWT token and returns a single-use ticket
    that can be used to authenticate WebSocket connections. The ticket includes
    the client's IP address for additional security.

    Rate limited to prevent abuse: 10 tickets per minute per user.
    """
    # Verify the JWT token
    clean_token = token.removeprefix("Bearer ")
    user_claims = verify_jwt_token(clean_token, jwks_client, CLIENT_ID, signing_algos)

    # Rate limiting check
    current_time = time.time()
    user_requests = ticket_rate_limit[user_claims.sub]

    # Remove old requests (older than 1 minute)
    user_requests[:] = [
        req_time for req_time in user_requests if current_time - req_time < 60
    ]

    # Check if user exceeded rate limit
    if len(user_requests) >= TICKET_RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for user {user_claims.sub}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many ticket requests. Please wait before requesting another ticket.",
        )

    # Add current request timestamp
    user_requests.append(current_time)

    # Get client IP address
    if not request.client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine client IP address",
        )

    client_ip = request.client.host

    # Generate the ticket

    # Get the user from the database using the token endpoint
    # This is a temporary solution until we implement proper user lookup
    try:
        # Try to get the user from the database
        with session_manager.db.begin() as conn:
            result = conn.execute(
                sa.text("SELECT user_id FROM users WHERE oidc_id = :oidc_id"),
                {"oidc_id": user_claims.sub},
            ).one_or_none()

            if result is not None:
                # User exists, create a UserId from the string
                user_id = UserId.from_str(result.user_id)
            else:
                # User doesn't exist yet, use a fallback
                # In a real implementation, we would redirect to the token endpoint
                # or create the user here
                logger.warning(
                    f"User {user_claims.sub} not found in database. Using fallback."
                )
                raise ValueError("User not found")
    except Exception as e:
        # Fallback to using the token endpoint first
        logger.warning(f"Error looking up user: {e}. Redirecting to /auth/token first.")
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Please authenticate with /auth/token first",
            headers={"Location": "/auth/token"},
        )

    # Generate the ticket using the user ID
    ticket = session_manager.ticket_store.generate_ticket(user_id, client_ip)

    logger.info(
        f"Generated WebSocket ticket {ticket.ticket_id} for user {user_claims.sub} from IP {client_ip}"
    )

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        expires_in=int(ticket.expires_at - ticket.created_at),
    )


@app.get("/auth/token")
async def get_user_token(token: Annotated[str, Depends(oidc_scheme)]):
    """
    Get user information, create the user in the database if needed, and return a clean token.

    This endpoint verifies the JWT token, then it fetches detailed user information
    from the OIDC provider using the token and the userinfo endpoint from the
    provider's well-known configuration.

    This endpoint must be called before requesting a ticket, as it ensures the user
    exists in the database.
    """
    clean_token = token.removeprefix("Bearer ")

    # Verify the token first
    user_claims = verify_jwt_token(clean_token, jwks_client, CLIENT_ID, signing_algos)

    try:
        # Get the userinfo endpoint from the OIDC provider's configuration
        userinfo_endpoint = await get_oidc_userinfo_endpoint(
            session_manager.get_settings().oidc_authority
        )

        # Get detailed user info from the OIDC provider
        user_info = await get_user_info_from_oidc_provider(
            clean_token, userinfo_endpoint
        )

        # Get / Create user in the database
        user_name = user_info.name or user_claims.name or "User"
        db_user = get_or_add_user(session_manager.db, user_claims.sub, user_name)

        # Return the combined information
        return {
            "token": clean_token,
            "user": {
                "sub": user_info.sub,
                "name": user_info.name,
                "email": user_info.email,
                "picture": user_info.picture,
                "given_name": user_info.given_name,
                "family_name": user_info.family_name,
                "username": user_info.username,
                "custom_attributes": user_info.custom_attributes,
                "db_user_id": str(db_user.user_id),  # Include the database user ID
            },
            "expires_at": user_claims.exp,
        }
    except Exception as e:
        # Fallback to basic claims if OIDC user info fails
        logger.warning(f"Failed to get OIDC user info: {e}. Using basic claims.")

        # Get / Create user in the database using basic claims
        user_name = user_claims.name or "User"
        db_user = get_or_add_user(session_manager.db, user_claims.sub, user_name)

        return {
            "token": clean_token,
            "user": {
                "sub": user_claims.sub,
                "name": user_claims.name,
                "email": user_claims.email,
                "picture": getattr(user_claims, "picture", None),
                "db_user_id": str(db_user.user_id),  # Include the database user ID
            },
            "expires_at": user_claims.exp,
        }


@app.get("/secured")
async def secured(token: Annotated[str, Depends(oidc_scheme)]):
    """
    Example secured endpoint that requires authentication.

    This endpoint demonstrates how to use the get_oidc_userinfo_endpoint and
    get_user_info_from_oidc_provider functions to fetch detailed user information
    from any OIDC provider.
    """
    clean_token = token.removeprefix("Bearer ")

    # Verify the token first
    user_claims = verify_jwt_token(clean_token, jwks_client, CLIENT_ID, signing_algos)

    try:
        # Get the userinfo endpoint from the OIDC provider's configuration
        userinfo_endpoint = await get_oidc_userinfo_endpoint(
            session_manager.get_settings().oidc_authority
        )

        # Get detailed user info from the OIDC provider
        user_info = await get_user_info_from_oidc_provider(
            clean_token, userinfo_endpoint
        )

        return {
            "message": "Access granted to secured endpoint",
            "user": {
                "sub": user_info.sub,
                "name": user_info.name,
                "email": user_info.email,
                "picture": user_info.picture,
                "given_name": user_info.given_name,
                "family_name": user_info.family_name,
                "username": user_info.username,
                "custom_attributes": user_info.custom_attributes,
            },
        }
    except Exception as e:
        # Fallback to basic claims if OIDC user info fails
        logger.warning(f"Failed to get OIDC user info: {e}. Using basic claims.")
        return {
            "message": "Access granted to secured endpoint",
            "user": {
                "sub": user_claims.sub,
                "name": user_claims.name,
                "email": user_claims.email,
            },
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, ticket_id: str | None):
    """
    WebSocket endpoint with ticket-based authentication.

    Clients should first obtain a ticket from /auth/ticket and then pass it
    as a query parameter: /ws?ticket_id=<ticket_id>
    """
    # Authenticate the WebSocket connection using ticket
    if not ticket_id:
        await websocket.close(code=1008, reason="Authentication ticket required")
        return

    # Get client IP address
    if not websocket.client:
        await websocket.close(code=1008, reason="Unable to determine client IP")
        return

    client_ip = websocket.client.host

    try:
        # Validate the ticket
        ticket = session_manager.ticket_store.validate_ticket(ticket_id, client_ip)

        if not ticket:
            await websocket.close(
                code=1008, reason="Invalid or expired authentication ticket"
            )
            return

        logger.info(
            f"WebSocket connection authenticated for user: {str(ticket.user_id)[0:6]} using ticket {ticket_id}"
        )

        # Clean up the used ticket
        session_manager.ticket_store.cleanup_ticket(ticket_id)

    except Exception as e:
        logger.warning(f"WebSocket ticket validation failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await websocket.accept()
    context = await session_manager.new_session(user_id=ticket.user_id)
    print(f"Opened new session {context.session_id} for user {ticket.user_id}")

    cws = ConcurrentWebSocket(already_accepted_ws=websocket)

    try:
        async with cws:
            await context.register(WEBSOCKET, cws)

            while True:
                message = await cws.receive_message()

                if isinstance(message, WebRTCMessage):
                    await handle_webrtc_message(context, message)
                elif isinstance(message, PingMessage):
                    await cws.send_message(PingMessage())
                # handle other message types...
    except WebSocketDisconnect:
        await context.teardown()
        print(f"Closed session {context.session_id} for {ticket.user_id}")


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
