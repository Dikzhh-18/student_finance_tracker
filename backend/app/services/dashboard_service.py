"""Dashboard template context — assembled from services, not raw SQL."""

from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.config import DEFAULT_CATEGORIES, EXPENSE_CATEGORIES
from app.repositories.finance_repository import (
    get_summary,
    get_used_categories,
    list_transactions,
    resolve_analytics_month,
)
from app.services.finance_service import (
    chart_data_for_month,
    expense_by_category,
    get_monthly_comparison,
    get_transaction_or_none,
    list_budget_progress,
)


def redirect_home(**params: str | int | None) -> RedirectResponse:
    clean = {k: str(v) for k, v in params.items() if v not in (None, "")}
    query = f"?{urlencode(clean)}" if clean else ""
    return RedirectResponse(url=f"/{query}", status_code=303)


def build_dashboard_context(
    request: Request,
    *,
    tx_type: str | None = None,
    category: str | None = None,
    month: str | None = None,
    q: str | None = None,
    analytics_month: str | None = None,
    edit_id: int | None = None,
    form_data: dict | None = None,
    budget_form: dict | None = None,
    errors: list[str] | None = None,
    flash: str | None = None,
    flash_type: str = "success",
) -> dict:
    user_id = int(request.session["user_id"])
    summary = get_summary(user_id)
    editing = get_transaction_or_none(user_id, edit_id) if edit_id else None
    selected_analytics_month = resolve_analytics_month(user_id, analytics_month)
    monthly = get_monthly_comparison(user_id, selected_analytics_month)
    categories_spent = expense_by_category(user_id, selected_analytics_month)
    budgets = list_budget_progress(user_id, selected_analytics_month)

    if form_data is None and editing:
        form_data = {
            "type": editing.type,
            "amount": str(int(editing.amount))
            if float(editing.amount).is_integer()
            else str(editing.amount),
            "category": editing.category,
            "description": editing.description or "",
            "date": editing.date,
        }

    return {
        "request": request,
        "today": date.today(),
        "total_balance": summary["total_balance"],
        "total_income": summary["total_income"],
        "total_expense": summary["total_expense"],
        "transactions": list_transactions(
            user_id=user_id,
            tx_type=tx_type or None,
            category=category or None,
            month=month or None,
            q=q or None,
            limit=50,
        ),
        "categories": get_used_categories(user_id),
        "default_categories": DEFAULT_CATEGORIES,
        "expense_categories": EXPENSE_CATEGORIES,
        "filters": {
            "type": tx_type or "",
            "category": category or "",
            "month": month or "",
            "q": q or "",
        },
        "analytics_month": selected_analytics_month,
        "monthly": monthly,
        "expense_by_category": categories_spent,
        "chart_data": chart_data_for_month(user_id, selected_analytics_month).model_dump(),
        "analytics_chart_data": {
            "cashflow": {
                "labels": [monthly.previous_month_label, monthly.month_label],
                "income": [monthly.previous.total_income, monthly.current.total_income],
                "expense": [monthly.previous.total_expense, monthly.current.total_expense],
            },
            "budget": {
                "labels": [b.category for b in budgets],
                "spent": [b.spent for b in budgets],
                "limit": [b.monthly_limit for b in budgets],
            },
        },
        "budgets": budgets,
        "budget_form": budget_form
        or {
            "category": "",
            "limit": "",
        },
        "editing": editing,
        "form_data": form_data
        or {
            "type": "expense",
            "amount": "",
            "category": "",
            "description": "",
            "date": date.today().isoformat(),
        },
        "errors": errors or [],
        "flash": flash,
        "flash_type": flash_type,
    }
