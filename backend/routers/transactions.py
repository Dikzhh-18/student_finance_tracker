"""Transaction create / edit / delete routes."""

from datetime import date

from fastapi import APIRouter, Form, Request

from app.repositories.finance_repository import list_transactions
from app.services.dashboard_service import build_dashboard_context, redirect_home
from app.services.finance_service import (
    create_new_transaction,
    delete_transaction_by_id,
    get_transaction_or_none,
    persist_transaction,
    persist_transaction_update,
    update_existing_transaction,
)
from app.utils.templates import templates

router = APIRouter(tags=["transactions"])


@router.get("/transactions")
def transaction_history(
    request: Request,
    type: str | None = None,
    category: str | None = None,
    month: str | None = None,
    q: str | None = None,
    flash: str | None = None,
    flash_type: str = "success",
):
    context = build_dashboard_context(
        request,
        tx_type=type,
        category=category,
        month=month,
        q=q,
        flash=flash,
        flash_type=flash_type,
    )
    context["active_nav"] = "history"
    context["transactions"] = list_transactions(
        user_id=int(request.session["user_id"]),
        tx_type=type,
        category=category,
        month=month,
        q=q,
        limit=500,
    )
    return templates.TemplateResponse(
        request=request,
        name="pages/transaction_history.html",
        context=context,
    )


@router.get("/transactions/new")
def new_transaction_form(request: Request, type: str = "expense"):
    tx_type = type if type in {"income", "expense"} else "expense"
    context = build_dashboard_context(
        request,
        form_data={
            "type": tx_type,
            "amount": "",
            "category": "",
            "description": "",
            "date": date.today().isoformat(),
        },
    )
    context["active_nav"] = tx_type
    return templates.TemplateResponse(
        request=request,
        name="pages/transaction_form_page.html",
        context=context,
    )


@router.get("/transactions/{tx_id}/edit")
def edit_transaction_form(request: Request, tx_id: int):
    user_id = int(request.session["user_id"])
    transaction = get_transaction_or_none(user_id, tx_id)
    if transaction is None:
        return redirect_home(flash="Transaksi tidak ditemukan.", flash_type="error")

    context = build_dashboard_context(request, edit_id=tx_id)
    context["active_nav"] = transaction.type
    return templates.TemplateResponse(
        request=request,
        name="pages/transaction_form_page.html",
        context=context,
    )


@router.post("/transactions")
def add_transaction(
    request: Request,
    type: str = Form("expense"),
    amount: str = Form(""),
    category: str = Form(""),
    description: str = Form(""),
    date: str = Form(""),
):
    payload, errors = create_new_transaction(
        tx_type=type,
        amount=amount,
        category=category,
        description=description,
        date=date,
    )
    if errors:
        context = build_dashboard_context(
            request,
            form_data={
                "type": type,
                "amount": amount,
                "category": category,
                "description": description,
                "date": date,
            },
            errors=errors,
            flash_type="error",
        )
        context["active_nav"] = type if type in {"income", "expense"} else "expense"
        return templates.TemplateResponse(
            request=request,
            name="pages/transaction_form_page.html",
            context=context,
            status_code=400,
        )

    persist_transaction(int(request.session["user_id"]), payload)
    return redirect_home(flash="Transaksi berhasil ditambahkan.")


@router.post("/transactions/{tx_id}/edit")
def edit_transaction(
    request: Request,
    tx_id: int,
    type: str = Form("expense"),
    amount: str = Form(""),
    category: str = Form(""),
    description: str = Form(""),
    date: str = Form(""),
):
    payload, errors = update_existing_transaction(
        user_id=int(request.session["user_id"]),
        tx_id=tx_id,
        tx_type=type,
        amount=amount,
        category=category,
        description=description,
        date=date,
    )
    if errors:
        if errors == ["Transaksi tidak ditemukan."]:
            return redirect_home(flash="Transaksi tidak ditemukan.", flash_type="error")

        context = build_dashboard_context(
            request,
            edit_id=tx_id,
            form_data={
                "type": type,
                "amount": amount,
                "category": category,
                "description": description,
                "date": date,
            },
            errors=errors,
        )
        context["active_nav"] = type if type in {"income", "expense"} else "expense"
        return templates.TemplateResponse(
            request=request,
            name="pages/transaction_form_page.html",
            context=context,
            status_code=400,
        )

    persist_transaction_update(int(request.session["user_id"]), tx_id, payload)
    return redirect_home(flash="Transaksi berhasil diperbarui.")


@router.post("/transactions/{tx_id}/delete")
def remove_transaction(request: Request, tx_id: int):
    if delete_transaction_by_id(int(request.session["user_id"]), tx_id):
        return redirect_home(flash="Transaksi berhasil dihapus.")
    return redirect_home(flash="Transaksi tidak ditemukan.", flash_type="error")
