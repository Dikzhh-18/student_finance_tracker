"""Form parsing and validation utilities."""

from __future__ import annotations

from datetime import datetime

from app.config import ALLOWED_TYPES


def parse_amount(raw: str) -> float | None:
    s = raw.strip().replace(" ", "")
    if not s:
        return None

    if s.count(",") == 1 and s.count(".") >= 1:
        cleaned = s.replace(".", "").replace(",", ".")
    elif s.count(",") == 0 and s.count(".") > 1:
        cleaned = s.replace(".", "")
    elif s.count(",") == 0 and s.count(".") == 1:
        left, right = s.split(".")
        cleaned = left + right if len(right) == 3 and left.isdigit() else s
    elif s.count(",") == 1 and s.count(".") == 0:
        cleaned = s.replace(",", ".")
    else:
        cleaned = s.replace(".", "").replace(",", "")

    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_date(raw: str) -> str | None:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def validate_transaction(
    *,
    tx_type: str,
    amount_raw: str,
    category: str,
    description: str,
    date_raw: str,
) -> tuple[dict | None, list[str]]:
    errors: list[str] = []

    if tx_type not in ALLOWED_TYPES:
        errors.append("Tipe transaksi tidak valid.")

    amount = parse_amount(amount_raw)
    if amount is None:
        errors.append("Jumlah harus angka lebih dari 0.")

    category_clean = category.strip()
    if not category_clean:
        errors.append("Kategori wajib diisi.")

    parsed_date = parse_date(date_raw)
    if parsed_date is None:
        errors.append("Tanggal tidak valid.")

    if errors:
        return None, errors

    return (
        {
            "tx_type": tx_type,
            "amount": amount,
            "category": category_clean,
            "description": description.strip(),
            "date": parsed_date,
        },
        [],
    )


def validate_budget(
    *,
    category: str,
    limit_raw: str,
) -> tuple[dict | None, list[str]]:
    errors: list[str] = []

    category_clean = category.strip()
    if not category_clean:
        errors.append("Kategori budget wajib diisi.")

    monthly_limit = parse_amount(limit_raw)
    if monthly_limit is None:
        errors.append("Limit bulanan harus angka lebih dari 0.")

    if errors:
        return None, errors

    return (
        {
            "category": category_clean,
            "monthly_limit": monthly_limit,
        },
        [],
    )
