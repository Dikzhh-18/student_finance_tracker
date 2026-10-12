"""Pydantic models for transactions, budgets, and analytics."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.utils.validators import parse_amount, parse_date


def _require_amount(value: Any, message: str) -> float:
    if isinstance(value, str):
        parsed = parse_amount(value)
        if parsed is None:
            raise ValueError(message)
        return parsed
    if isinstance(value, (int, float)) and float(value) > 0:
        return float(value)
    raise ValueError(message)


class TransactionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    category: str = Field(min_length=1)
    description: str = ""
    date: str

    @field_validator("amount", mode="before")
    @classmethod
    def parse_form_amount(cls, value: Any) -> float:
        return _require_amount(value, "Jumlah harus angka lebih dari 0.")

    @field_validator("category", "description", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str:
        return str(value).strip() if value is not None else ""

    @field_validator("date", mode="before")
    @classmethod
    def parse_form_date(cls, value: Any) -> str:
        if isinstance(value, date):
            return value.isoformat()
        parsed = parse_date(str(value or ""))
        if parsed is None:
            raise ValueError("Tanggal tidak valid.")
        return parsed

    def to_repo(self) -> dict[str, Any]:
        return {
            "tx_type": self.type,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
        }


class TransactionOut(BaseModel):
    id: int
    type: Literal["income", "expense"]
    amount: float
    category: str
    description: str = ""
    date: str
    created_at: str | None = None


class BudgetCreate(BaseModel):
    category: str = Field(min_length=1)
    monthly_limit: float = Field(gt=0)

    @field_validator("monthly_limit", mode="before")
    @classmethod
    def parse_limit(cls, value: Any) -> float:
        return _require_amount(value, "Limit bulanan harus angka lebih dari 0.")

    @field_validator("category", mode="before")
    @classmethod
    def strip_category(cls, value: Any) -> str:
        return str(value).strip() if value is not None else ""


class BudgetRecord(BaseModel):
    id: int
    category: str
    monthly_limit: float


class BudgetProgress(BudgetRecord):
    spent: float
    remaining: float
    percent: float
    raw_percent: float
    over_budget: bool

    @computed_field
    @property
    def bar_class(self) -> str:
        if self.over_budget:
            return "bg-rose-500"
        if self.percent >= 80:
            return "bg-amber-400"
        return "bg-indigo-500"


class MoneySummary(BaseModel):
    total_income: float
    total_expense: float
    total_balance: float


class CategoryTotal(BaseModel):
    category: str
    total: float


class MonthlyComparison(BaseModel):
    month: str
    month_label: str
    previous_month: str
    previous_month_label: str
    current: MoneySummary
    previous: MoneySummary
    delta_income: float
    delta_expense: float
    delta_balance: float


class ChartData(BaseModel):
    labels: list[str]
    values: list[float]
