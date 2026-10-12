"""Business logic for transactions, budgets, and analytics."""

from __future__ import annotations

from pydantic import ValidationError

from app.config import MONTH_NAMES_ID
from app.repositories import finance_repository as repo
from app.schemas import (
    BudgetCreate,
    BudgetProgress,
    BudgetRecord,
    CategoryTotal,
    ChartData,
    MoneySummary,
    MonthlyComparison,
    TransactionCreate,
    TransactionOut,
)


FIELD_ERRORS = {
    "type": "Tipe transaksi tidak valid.",
    "amount": "Jumlah harus angka lebih dari 0.",
    "category": "Kategori wajib diisi.",
    "date": "Tanggal tidak valid.",
    "monthly_limit": "Limit bulanan harus angka lebih dari 0.",
}


def _errors_from_validation(exc: ValidationError, *, budget: bool = False) -> list[str]:
    messages: list[str] = []
    for err in exc.errors():
        field = err.get("loc", (None,))[0]
        if budget and field == "category":
            text = "Kategori budget wajib diisi."
        else:
            text = FIELD_ERRORS.get(str(field), err.get("msg", "Input tidak valid."))
        if text not in messages:
            messages.append(text)
    return messages


def format_month_label(month: str) -> str:
    try:
        year, month_num = month.split("-")
        return f"{MONTH_NAMES_ID[int(month_num)]} {year}"
    except (ValueError, KeyError, IndexError):
        return month


def previous_month(month: str) -> str:
    year, month_num = map(int, month.split("-"))
    if month_num == 1:
        return f"{year - 1}-12"
    return f"{year}-{month_num - 1:02d}"


def money_summary(raw: dict) -> MoneySummary:
    return MoneySummary.model_validate(raw)


def get_monthly_comparison(user_id: int, month: str) -> MonthlyComparison:
    prev = previous_month(month)
    current = money_summary(repo.get_month_summary(user_id, month))
    previous = money_summary(repo.get_month_summary(user_id, prev))
    return MonthlyComparison(
        month=month,
        month_label=format_month_label(month),
        previous_month=prev,
        previous_month_label=format_month_label(prev),
        current=current,
        previous=previous,
        delta_income=current.total_income - previous.total_income,
        delta_expense=current.total_expense - previous.total_expense,
        delta_balance=current.total_balance - previous.total_balance,
    )


def expense_by_category(user_id: int, month: str) -> list[CategoryTotal]:
    return [CategoryTotal.model_validate(row) for row in repo.get_expense_by_category(user_id, month)]


def chart_data_for_month(user_id: int, month: str) -> ChartData:
    items = expense_by_category(user_id, month)
    return ChartData(
        labels=[item.category for item in items],
        values=[item.total for item in items],
    )


def list_budget_progress(user_id: int, month: str) -> list[BudgetProgress]:
    progress: list[BudgetProgress] = []
    for row in repo.list_budget_records(user_id):
        record = BudgetRecord.model_validate(row)
        spent = repo.get_category_spent(user_id, record.category, month)
        percent = (spent / record.monthly_limit * 100) if record.monthly_limit > 0 else 0
        progress.append(
            BudgetProgress(
                **record.model_dump(),
                spent=spent,
                remaining=record.monthly_limit - spent,
                percent=min(percent, 100),
                raw_percent=percent,
                over_budget=spent > record.monthly_limit,
            )
        )
    return progress


def create_new_transaction(
    *,
    tx_type: str,
    amount: str,
    category: str,
    description: str,
    date: str,
) -> tuple[TransactionCreate | None, list[str]]:
    try:
        return (
            TransactionCreate.model_validate(
                {
                    "type": tx_type,
                    "amount": amount,
                    "category": category,
                    "description": description,
                    "date": date,
                }
            ),
            [],
        )
    except ValidationError as exc:
        return None, _errors_from_validation(exc)


def update_existing_transaction(
    *,
    user_id: int,
    tx_id: int,
    tx_type: str,
    amount: str,
    category: str,
    description: str,
    date: str,
) -> tuple[TransactionCreate | None, list[str]]:
    if not repo.get_transaction(user_id, tx_id):
        return None, ["Transaksi tidak ditemukan."]
    return create_new_transaction(
        tx_type=tx_type,
        amount=amount,
        category=category,
        description=description,
        date=date,
    )


def persist_transaction(user_id: int, payload: TransactionCreate) -> int:
    return repo.create_transaction(user_id=user_id, **payload.to_repo())


def persist_transaction_update(user_id: int, tx_id: int, payload: TransactionCreate) -> bool:
    return repo.update_transaction(user_id, tx_id, **payload.to_repo())


def delete_transaction_by_id(user_id: int, tx_id: int) -> bool:
    return repo.delete_transaction(user_id, tx_id)


def get_transaction_or_none(user_id: int, tx_id: int) -> TransactionOut | None:
    row = repo.get_transaction(user_id, tx_id)
    return TransactionOut.model_validate(row) if row else None


def save_budget_payload(*, category: str, limit: str) -> tuple[BudgetCreate | None, list[str]]:
    try:
        return (
            BudgetCreate.model_validate(
                {
                    "category": category,
                    "monthly_limit": limit,
                }
            ),
            [],
        )
    except ValidationError as exc:
        return None, _errors_from_validation(exc, budget=True)


def upsert_budget_payload(user_id: int, payload: BudgetCreate) -> None:
    repo.upsert_budget(
    user_id=user_id,
        category=payload.category,
        monthly_limit=payload.monthly_limit,
    )


def delete_budget_by_id(user_id: int, budget_id: int) -> bool:
    return repo.delete_budget(user_id, budget_id)
