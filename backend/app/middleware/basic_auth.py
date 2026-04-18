"""Optional HTTP Basic authentication for all routes."""

from __future__ import annotations

import base64
import binascii
import logging
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger(__name__)


class OptionalBasicAuthMiddleware(BaseHTTPMiddleware):
    """When EK_BASIC_AUTH_USER and EK_BASIC_AUTH_PASSWORD are set, require valid Basic credentials."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        user = (settings.basic_auth_user or "").strip()
        password = settings.basic_auth_password or ""
        if not user or not password:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return _challenge()

        try:
            raw = base64.b64decode(auth[6:].strip(), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return _challenge()

        if ":" not in raw:
            return _challenge()

        u, _, p = raw.partition(":")
        if not secrets.compare_digest(u, user) or not secrets.compare_digest(p, password):
            logger.warning("Basic auth failed for path %s", request.url.path)
            return _challenge()

        return await call_next(request)


def _challenge() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Kirjautuminen vaaditaan (HTTP Basic)."},
        headers={"WWW-Authenticate": 'Basic realm="Etelä-Karjala ICT"'},
    )
