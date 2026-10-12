"""Registration, login, and logout routes."""

from urllib.parse import urlparse
from datetime import date

from fastapi import APIRouter, File, Form, Request, UploadFile
from starlette.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from fastapi.responses import Response

from app.repositories.finance_repository import get_user_by_id
from app.services.auth_service import (
    RegistrationError,
    authenticate_account,
    get_account_by_id,
    remove_avatar,
    register_account,
    save_avatar,
    save_theme,
    update_profile,
)
from app.utils.templates import templates

router = APIRouter(tags=["authentication"])


def _safe_next(value: str) -> str:
    parsed = urlparse(value)
    if value.startswith("/") and not value.startswith("//") and not parsed.netloc:
        return value
    return "/"


@router.get("/login")
def login_page(request: Request, next: str = "/", error: str | None = None):
    if request.session.get("user_id"):
        return RedirectResponse(_safe_next(next), status_code=303)
    return templates.TemplateResponse(request=request, name="pages/login.html", context={"request": request, "next": _safe_next(next), "error": error})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form("/"),
):
    user = authenticate_account(email=email, password=password)
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="pages/login.html",
            context={"request": request, "next": _safe_next(next), "error": "Email atau kata sandi tidak sesuai."},
            status_code=400,
        )
    request.session.clear()
    request.session.update({"user_id": user["id"], "user_name": user["name"], "user_email": user["email"], "theme": user["theme"], "has_avatar": bool(user["has_avatar"])})
    return RedirectResponse(_safe_next(next), status_code=303)


@router.get("/register")
def register_page(request: Request, error: str | None = None):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request=request, name="pages/register.html", context={"request": request, "error": error})


@router.post("/register")
def register(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    password_confirmation: str = Form(""),
):
    if password != password_confirmation:
        error = "Konfirmasi kata sandi tidak cocok."
    else:
        try:
            user_id = register_account(name=name, email=email, password=password)
        except RegistrationError as exc:
            error = str(exc)
        except IntegrityError:
            error = "Email tersebut sudah terdaftar."
        else:
            user = get_user_by_id(user_id)
            request.session.clear()
            request.session.update({"user_id": user_id, "user_name": user["name"], "user_email": user["email"], "theme": user["theme"], "has_avatar": bool(user["has_avatar"])})
            return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="pages/register.html",
        context={"request": request, "error": error},
        status_code=400,
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.post("/account/profile")
def save_account_profile(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
):
    user_id = int(request.session["user_id"])
    try:
        name, email = update_profile(user_id=user_id, name=name, email=email)
    except RegistrationError as exc:
        user = get_account_by_id(user_id)
        return templates.TemplateResponse(
            request=request,
            name="pages/account.html",
            context={"request": request, "active_nav": "account", "user": user, "today": date.today(), "flash": str(exc), "flash_type": "error"},
            status_code=400,
        )
    except IntegrityError:
        user = get_account_by_id(user_id)
        return templates.TemplateResponse(
            request=request,
            name="pages/account.html",
            context={"request": request, "active_nav": "account", "user": user, "today": date.today(), "flash": "Email tersebut sudah digunakan akun lain.", "flash_type": "error"},
            status_code=400,
        )
    request.session.update({"user_name": name, "user_email": email})
    return RedirectResponse("/account?flash=Profil+berhasil+diperbarui", status_code=303)


@router.post("/account/theme/select")
def select_account_theme(request: Request, theme: str = Form("light")):
    user_id = int(request.session["user_id"])
    try:
        theme = save_theme(user_id=user_id, theme=theme)
    except RegistrationError as exc:
        user = get_account_by_id(user_id)
        return templates.TemplateResponse(
            request=request,
            name="pages/account.html",
            context={"request": request, "active_nav": "account", "user": user, "today": date.today(), "flash": str(exc), "flash_type": "error"},
            status_code=400,
        )
    request.session["theme"] = theme
    return RedirectResponse("/account", status_code=303)


@router.post("/account/theme")
def save_account_theme(request: Request, theme: str = Form("light")):
    user_id = int(request.session["user_id"])
    try:
        theme = save_theme(user_id=user_id, theme=theme)
    except RegistrationError:
        return RedirectResponse("/account?flash=Pilihan+tema+tidak+valid&flash_type=error", status_code=303)
    request.session["theme"] = theme
    return RedirectResponse("/account", status_code=303)


@router.post("/account/avatar")
async def upload_account_avatar(request: Request, avatar: UploadFile | None = File(default=None)):
    user_id = int(request.session["user_id"])
    if avatar is None:
        error = "Pilih file foto terlebih dahulu."
    else:
        raw = await avatar.read(2 * 1024 * 1024 + 1)
        try:
            save_avatar(user_id=user_id, raw=raw)
        except RegistrationError as exc:
            error = str(exc)
        else:
            request.session["has_avatar"] = True
            return RedirectResponse("/account?flash=Foto+profil+berhasil+diperbarui", status_code=303)
    user = get_account_by_id(user_id)
    return templates.TemplateResponse(
        request=request,
        name="pages/account.html",
        context={"request": request, "active_nav": "account", "user": user, "today": date.today(), "flash": error, "flash_type": "error"},
        status_code=400,
    )


@router.post("/account/avatar/remove")
def delete_account_avatar(request: Request):
    remove_avatar(user_id=int(request.session["user_id"]))
    request.session["has_avatar"] = False
    return RedirectResponse("/account?flash=Foto+profil+dihapus", status_code=303)
