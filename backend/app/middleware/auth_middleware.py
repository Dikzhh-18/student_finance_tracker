"""Require an authenticated session for personal finance pages and actions."""

from urllib.parse import quote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse


class AuthenticationMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = ("/login", "/register", "/health", "/static/")

    async def dispatch(self, request, call_next):
        if request.url.path in self.PUBLIC_PATHS or request.url.path.startswith("/static/"):
            return await call_next(request)
        user_id = request.session.get("user_id")
        if not isinstance(user_id, int):
            next_path = quote(request.url.path, safe="")
            return RedirectResponse(f"/login?next={next_path}", status_code=303)
        return await call_next(request)
