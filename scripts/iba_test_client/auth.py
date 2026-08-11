"""Keycloak authentication client for IBA test scripts.

Implements the Resource Owner Password Credentials (ROPC) grant flow
against the Keycloak ``/protocol/openid-connect/token`` endpoint.
Tokens are cached per email address and automatically re-acquired when
they expire (with a 60-second safety margin).

Typical usage:
    kc = KeycloakClient(
        url="https://auth.keycenter.ai/auth",
        realm="keycenter",
        client_id="web",
        client_secret="<secret>",
    )
    token = kc.get_valid_token("user@example.com", "password")
    # Pass `token` to IBAChatClient as Bearer token.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass

import requests

log = logging.getLogger("iba-test-auth")


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_at: float  # unix timestamp


class KeycloakClient:
    """Manages Keycloak JWT tokens with per-user caching and auto-refresh."""

    def __init__(self, url: str, realm: str, client_id: str, client_secret: str):
        self.url = url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self._token_endpoint = (
            f"{self.url}/realms/{self.realm}/protocol/openid-connect/token"
        )
        self._cache: dict[str, TokenPair] = {}

    def login(self, email: str, password: str) -> TokenPair:
        """Authenticate via ROPC grant and return a TokenPair.

        Args:
            email: Keycloak username or email.
            password: Keycloak password.

        Returns:
            TokenPair with access_token, refresh_token, expires_at.

        Raises:
            requests.HTTPError: If authentication fails.
        """
        r = requests.post(
            self._token_endpoint,
            data={
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": email,
                "password": password,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        expires_at = time.time() + data.get("expires_in", 300)
        pair = TokenPair(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=expires_at,
        )
        self._cache[email] = pair
        log.info("Login OK for %s (exp in %ds)", email, data.get("expires_in", 300))
        return pair

    def get_valid_token(self, email: str, password: str) -> str:
        """Return a valid access_token, using cache or re-authenticating.

        Args:
            email: Keycloak username or email.
            password: Keycloak password.

        Returns:
            A valid access_token string.
        """
        cached = self._cache.get(email)
        if cached and time.time() < cached.expires_at - 60:
            return cached.access_token
        pair = self.login(email, password)
        return pair.access_token

    def get_user_pool(self, users: list[dict[str, str]]) -> list[str]:
        """Pre-authenticate a list of users and return their tokens.

        Args:
            users: List of {"email": ..., "password": ...} dicts.

        Returns:
            List of access_token strings.
        """
        tokens = []
        for u in users:
            token = self.get_valid_token(u["email"], u["password"])
            tokens.append(token)
        return tokens

    @staticmethod
    def decode_claims(token: str) -> dict:
        """Decode JWT payload without signature verification.

        Args:
            token: JWT access_token string.

        Returns:
            Decoded claims dict.
        """
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))

    @staticmethod
    def get_account_id(token: str) -> str:
        """Extract the `sub` claim from a JWT token.

        Args:
            token: JWT access_token string.

        Returns:
            The `sub` claim value (account ID).
        """
        return KeycloakClient.decode_claims(token).get("sub", "")
