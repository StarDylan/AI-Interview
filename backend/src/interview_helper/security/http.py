from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from fastapi import status
from typing import List, Optional, Dict, Any
import jwt


class TokenError(HTTPException):
    def __init__(self, detail: str, code=status.HTTP_401_UNAUTHORIZED):
        super().__init__(
            status_code=code, detail=detail, headers={"WWW-Authenticate": "Bearer"}
        )


class TokenClaims(BaseModel):
    # ---- JWT standard claims ----
    iss: str  # Issuer Identifier (MUST match your IdP's issuer URL)
    sub: str  # Subject Identifier (unique user ID)
    exp: int  # Expiration time (epoch seconds)
    iat: int  # Issued-at time (epoch seconds)

    # ---- Recommended but optional ----
    nbf: Optional[int] = None  # Not-before (epoch seconds)
    jti: Optional[str] = None  # JWT ID (unique identifier for this token)

    # ---- OIDC standard claims ----
    auth_time: Optional[int] = None  # Time of user authentication
    nonce: Optional[str] = None  # Nonce (if supplied in the auth request)

    # ---- Profile/email OIDC scopes ----
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None

    # ---- Roles/scopes ----
    scope: Optional[str] = None  # space-delimited list of granted scopes
    roles: Optional[List[str]] = (
        None  # IdP-specific claim (sometimes "roles", "groups", etc.)
    )

    # ---- Allow custom claims ----
    extra: Dict[str, Any] = {}


def verify_jwt_token(
    token: str, jwks_client: jwt.PyJWKClient, client_id: str, signing_algos: str
) -> TokenClaims:
    print(token)
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            key=signing_key,
            algorithms=signing_algos,
        )
    except InvalidTokenError as e:
        raise TokenError(f"Invalid token: {e}")

    # normalize scopes/roles here...
    return TokenClaims(**payload)
