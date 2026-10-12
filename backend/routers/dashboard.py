"""Dashboard page routes."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from datetime import date

from app.repositories.finance_repository import get_user_avatar
from app.services.auth_service import get_account_by_id
from app.services.dashboard_service import build_dashboard_context
from app.utils.templates import templates

router = APIRouter(tags=["dashboard"])


@router.get("/health")
def health_check():
    """Public health check without exposing personal financial information."""
    return JSONResponse(
        content={
            "status": "ok",
            "service": "student-finance-tracker",
        }
    )


@router.get("/")
def home(
    request: Request,
    type: str | None = Query(default=None),
    category: str | None = None,
    month: str | None = None,
    q: str | None = None,
    analytics_month: str | None = None,
    edit: int | None = None,
    flash: str | None = None,
    flash_type: str = "success",
):
    context = build_dashboard_context(
        request,
        tx_type=type,
        category=category,
        month=month,
        q=q,
        analytics_month=analytics_month,
        edit_id=edit,
        flash=flash,
        flash_type=flash_type,
    )
    context["active_nav"] = "dashboard"
    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context=context,
    )


@router.get("/analytics")
def analytics(
    request: Request,
    analytics_month: str | None = None,
    flash: str | None = None,
    flash_type: str = "success",
):
    context = build_dashboard_context(
        request,
        analytics_month=analytics_month,
        flash=flash,
        flash_type=flash_type,
    )
    context["active_nav"] = "analytics"
    return templates.TemplateResponse(
        request=request,
        name="pages/analytics.html",
        context=context,
    )


@router.get("/account")
def account(
    request: Request,
    flash: str | None = None,
    flash_type: str = "success",
):
    user = get_account_by_id(int(request.session["user_id"]))
    return templates.TemplateResponse(
        request=request,
        name="pages/account.html",
        context={"request": request, "active_nav": "account", "user": user, "today": date.today(), "flash": flash, "flash_type": flash_type},
    )


@router.get("/account/avatar")
def account_avatar(request: Request):
    avatar = get_user_avatar(int(request.session["user_id"]))
    if avatar is None:
        return Response(status_code=404)
    image, content_type = avatar
    return Response(
        content=image,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
