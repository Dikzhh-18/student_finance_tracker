"""Budget create / update / delete routes."""

from fastapi import APIRouter, Form, Request

from app.services.dashboard_service import build_dashboard_context, redirect_home
from app.services.finance_service import delete_budget_by_id, save_budget_payload, upsert_budget_payload
from app.utils.templates import templates

router = APIRouter(tags=["budgets"])


@router.post("/budgets")
def save_budget(
    request: Request,
    category: str = Form(""),
    limit: str = Form(""),
):
    payload, errors = save_budget_payload(category=category, limit=limit)
    if errors:
        context = build_dashboard_context(
            request,
            budget_form={"category": category, "limit": limit},
            errors=errors,
            flash_type="error",
        )
        context["active_nav"] = "dashboard"
        return templates.TemplateResponse(
            request=request,
            name="pages/dashboard.html",
            context=context,
            status_code=400,
        )

    upsert_budget_payload(int(request.session["user_id"]), payload)
    return redirect_home(flash=f"Budget {payload.category} disimpan.")


@router.post("/budgets/{budget_id}/delete")
def remove_budget(request: Request, budget_id: int):
    if delete_budget_by_id(int(request.session["user_id"]), budget_id):
        return redirect_home(flash="Budget dihapus.")
    return redirect_home(flash="Budget tidak ditemukan.", flash_type="error")
