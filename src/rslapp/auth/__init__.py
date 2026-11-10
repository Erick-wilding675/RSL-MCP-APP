"""Autenticação OAuth 2.1 do modo HTTP do RSL.app (D-015, D-016)."""

from __future__ import annotations

from rslapp.auth.provider import (
    AUTH_CODE_TTL_SECONDS,
    IP_RATE_LIMIT_WINDOW_SECONDS,
    MAX_WRONG_CODES_PER_IP,
    MAX_WRONG_CODES_PER_REQUEST,
    PENDING_AUTH_TTL_SECONDS,
    PendingAuthRequest,
    RSLOAuthProvider,
    build_auth_routes,
)
from rslapp.auth.store import (
    AuthStore,
    RSLAccessToken,
    RSLAuthorizationCode,
    RSLRefreshToken,
    StoredToken,
    hash_token,
    normalize_resource_url,
)
from rslapp.auth.verifier import RSLTokenVerifier, current_person_id

__all__ = [
    "AUTH_CODE_TTL_SECONDS",
    "IP_RATE_LIMIT_WINDOW_SECONDS",
    "MAX_WRONG_CODES_PER_IP",
    "MAX_WRONG_CODES_PER_REQUEST",
    "PENDING_AUTH_TTL_SECONDS",
    "AuthStore",
    "PendingAuthRequest",
    "RSLAccessToken",
    "RSLAuthorizationCode",
    "RSLOAuthProvider",
    "RSLRefreshToken",
    "RSLTokenVerifier",
    "StoredToken",
    "build_auth_routes",
    "current_person_id",
    "hash_token",
    "normalize_resource_url",
]
