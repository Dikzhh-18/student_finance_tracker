"""App entrypoint — wires lifespan, static files, sessions, CSRF, and routers."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import FRONTEND_DIR
from app.middleware.auth_middleware import AuthenticationMiddleware
from app.middleware.csrf_middleware import CSRFProtectionMiddleware
from app.repositories.finance_repository import init_db
from app.utils.templates import templates
from routers import auth, budgets, dashboard, transactions

SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "local-development-key-change-this-before-deploying")
if not os.getenv("SESSION_SECRET_KEY") and os.getenv("VERCEL"):
    raise RuntimeError("Set SESSION_SECRET_KEY in Vercel environment variables.")
if os.getenv("VERCEL") and len(SECRET_KEY) < 32:
    raise RuntimeError("SESSION_SECRET_KEY must contain at least 32 characters on Vercel.")
if os.getenv("VERCEL") and not os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
    raise RuntimeError("Set DATABASE_URL to the Supabase PostgreSQL transaction-pooler URL in Vercel.")

templates.env.globals["get_csrf_token"] = lambda request: request.session.setdefault(
    "csrf_token", __import__("secrets", fromlist=["token_urlsafe"]).token_urlsafe(32)
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Student Finance Tracker", lifespan=lifespan)
app.add_middleware(CSRFProtectionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "true" if os.getenv("VERCEL") else "false").lower() == "true",
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(auth.router)
