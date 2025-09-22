from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from fastapi import status
from typing import List, Optional, Dict, Any, Union
import jwt
import httpx
import json
import logging
from interview_helper.config import Settings

logger = logging.getLogger(__name__)


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


class OIDCUserInfo(BaseModel):
    """Model for OIDC provider user information"""
    sub: str
    username: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    phone_number: Optional[str] = None
    phone_number_verified: Optional[bool] = None
    custom_attributes: Dict[str, Any] = {}


async def get_user_info_from_oidc_provider(
    token: str, 
    userinfo_endpoint: str,
) -> OIDCUserInfo:
    """
    Get user information from an OIDC provider using the access token.
    
    Args:
        token: The access token from the OIDC provider (without 'Bearer ' prefix)
        userinfo_endpoint: The userinfo endpoint URL from the OIDC provider
        
    Returns:
        OIDCUserInfo: User information from the OIDC provider
        
    Raises:
        TokenError: If the token is invalid or the request fails
    """
    # Remove 'Bearer ' prefix if present
    clean_token = token.removeprefix("Bearer ")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {clean_token}"},
            )
            
            if response.status_code != 200:
                raise TokenError(
                    f"Failed to get user info: {response.status_code} {response.text}",
                    code=status.HTTP_401_UNAUTHORIZED,
                )
                
            user_data = response.json()
            
            # Extract standard claims
            standard_claims = {
                "sub", "username", "email", "email_verified", "name", 
                "given_name", "family_name", "picture", "phone_number", 
                "phone_number_verified"
            }
            
            # Separate standard claims from custom attributes
            standard_user_data = {k: v for k, v in user_data.items() if k in standard_claims}
            custom_attributes = {k: v for k, v in user_data.items() if k not in standard_claims}
            
            # Add custom attributes to the standard data
            standard_user_data["custom_attributes"] = custom_attributes
            
            return OIDCUserInfo(**standard_user_data)
            
    except httpx.RequestError as e:
        raise TokenError(f"Error connecting to OIDC provider: {e}")
    except json.JSONDecodeError:
        raise TokenError("Invalid response from OIDC provider")
    except Exception as e:
        raise TokenError(f"Failed to get user info: {e}")


async def get_oidc_userinfo_endpoint(oidc_authority: str) -> str:
    """
    Get the userinfo endpoint from the OIDC provider's well-known configuration.
    
    Args:
        oidc_authority: The base URL of the OIDC provider (e.g., https://cognito-idp.us-west-2.amazonaws.com/us-west-2_abc123)
        
    Returns:
        str: The userinfo endpoint URL
        
    Raises:
        TokenError: If the request fails or the userinfo_endpoint is not found in the configuration
    """
    # Ensure the authority URL doesn't end with a slash
    oidc_authority = oidc_authority.rstrip("/")
    
    # Construct the well-known configuration URL
    config_url = f"{oidc_authority}/.well-known/openid-configuration"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(config_url)
            
            if response.status_code != 200:
                raise TokenError(
                    f"Failed to get OIDC configuration: {response.status_code} {response.text}",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
                
            config_data = response.json()
            
            # Extract the userinfo endpoint
            userinfo_endpoint = config_data.get("userinfo_endpoint")
            
            if not userinfo_endpoint:
                raise TokenError(
                    "Userinfo endpoint not found in OIDC configuration",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
                
            logger.info(f"Found userinfo endpoint: {userinfo_endpoint}")
            return userinfo_endpoint
            
    except httpx.RequestError as e:
        raise TokenError(f"Error connecting to OIDC provider: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except json.JSONDecodeError:
        raise TokenError("Invalid response from OIDC provider", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        if not isinstance(e, TokenError):
            raise TokenError(f"Failed to get OIDC configuration: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise
