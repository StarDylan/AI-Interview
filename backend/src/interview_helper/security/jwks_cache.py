import time
from authlib.jose.rfc7517.key_set import KeySet
from typing import cast
from authlib.jose.rfc7517.jwk import JsonWebKey
import httpx


class JWKSCache:
    def __init__(self, OIDC_CONFIG_URL: str, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.expires_at = 0
        self.key_set = cast(KeySet | None, None)
        self.jwks_uri = None
        self.OIDC_CONFIG_URL = OIDC_CONFIG_URL

    async def _fetch_config_and_keys(self):
        async with httpx.AsyncClient(timeout=10) as client:
            cfg = (await client.get(self.OIDC_CONFIG_URL)).json()
            self.jwks_uri = cfg["jwks_uri"]

            jwks = (await client.get(self.jwks_uri)).json()
        self.key_set = JsonWebKey.import_key_set(jwks)
        self.expires_at = int(time.time()) + self.ttl

    async def get_keys(self) -> KeySet:
        now = int(time.time())
        if not self.key_set or now >= self.expires_at:
            await self._fetch_config_and_keys()

        assert self.key_set is not None
        return self.key_set

    async def refresh_on_kid_miss(self):
        # Force refresh (use when header.kid not found)
        self.expires_at = 0
        return await self.get_keys()
