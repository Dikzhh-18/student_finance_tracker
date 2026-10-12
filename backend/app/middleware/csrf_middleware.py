"""CSRF protection middleware for POST/PUT/DELETE forms."""

from __future__ import annotations

import secrets
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Protects state-changing requests with a synchronized CSRF token."""

    EXEMPT_PATHS = {"/health", "/static/"}

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)

        # Generate (or reuse) a token for this session
        token = request.session.get("csrf_token")
        if token is None:
            token = secrets.token_urlsafe(32)
            request.session["csrf_token"] = token

        # Validate token on state-changing requests without buffering uploads
        # through an additional request.form() parse in middleware.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            submitted_token = request.headers.get("x-csrf-token")
            content_type = request.headers.get("content-type", "")
            if submitted_token is None and content_type.startswith("application/x-www-form-urlencoded"):
                body = await request.body()
                from urllib.parse import parse_qs
                form = parse_qs(body.decode("utf-8", errors="replace"))
                values = form.get("csrf_token", [])
                submitted_token = values[0] if values else None
            elif submitted_token is None and content_type.startswith("multipart/form-data"):
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > 2_200_000:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(status_code=413, content={"detail": "Ukuran unggahan terlalu besar."})
                body = await request.body()
                if len(body) > 2_200_000:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(status_code=413, content={"detail": "Ukuran unggahan terlalu besar."})
                form = await request.form(max_files=1, max_fields=20, max_part_size=2_100_000)
                token_value = form.get("csrf_token")
                submitted_token = token_value if isinstance(token_value, str) else None
            stored = request.session.get("csrf_token")
            if not isinstance(submitted_token, str) or stored is None or not secrets.compare_digest(submitted_token, stored):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"detail": "CSRF token mismatch."})

        response = await call_next(request)
        return response
