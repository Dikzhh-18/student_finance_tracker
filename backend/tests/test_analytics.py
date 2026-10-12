from app.repositories.finance_repository import (
    create_transaction,
    get_expense_by_category,
    get_month_summary,
    resolve_analytics_month,
)
from app.services.finance_service import (
    chart_data_for_month,
    format_month_label,
    get_monthly_comparison,
    previous_month,
)


def _expense(user_id: int, amount: float, category: str, day: str) -> int:
    return create_transaction(
    user_id=user_id,
        tx_type="expense",
        amount=amount,
        category=category,
        description=category,
        date=day,
    )


def _income(user_id: int, amount: float, category: str, day: str) -> int:
    return create_transaction(
    user_id=user_id,
        tx_type="income",
        amount=amount,
        category=category,
        description=category,
        date=day,
    )


def test_previous_month_wraps_january():
    assert previous_month("2026-01") == "2025-12"
    assert previous_month("2026-10") == "2026-09"


def test_format_month_label_uses_indonesian_names():
    assert format_month_label("2026-03") == "Maret 2026"
    assert format_month_label("bad") == "bad"


def test_month_summary_and_expense_by_category(db_path, user_id):
    _income(user_id, 1_000_000, "Beasiswa", "2026-03-01")
    _expense(user_id, 200_000, "Makan", "2026-03-05")
    _expense(user_id, 100_000, "Makan", "2026-03-06")
    _expense(user_id, 150_000, "Transport", "2026-03-07")
    _expense(user_id, 50_000, "Makan", "2026-04-01")

    summary = get_month_summary(user_id, "2026-03")
    assert summary["total_income"] == 1_000_000
    assert summary["total_expense"] == 450_000
    assert summary["total_balance"] == 550_000

    by_category = get_expense_by_category(user_id, "2026-03")
    assert by_category[0] == {"category": "Makan", "total": 300_000.0}
    assert by_category[1] == {"category": "Transport", "total": 150_000.0}


def test_monthly_comparison_deltas(db_path, user_id):
    _income(user_id, 800_000, "Orang Tua", "2026-02-01")
    _expense(user_id, 100_000, "Makan", "2026-02-10")
    _income(user_id, 1_000_000, "Beasiswa", "2026-03-01")
    _expense(user_id, 250_000, "Kos", "2026-03-02")

    comparison = get_monthly_comparison(user_id, "2026-03")
    assert comparison.month_label == "Maret 2026"
    assert comparison.previous_month_label == "Februari 2026"
    assert comparison.current.total_income == 1_000_000
    assert comparison.current.total_expense == 250_000
    assert comparison.delta_income == 200_000
    assert comparison.delta_expense == 150_000
    assert comparison.delta_balance == 50_000


def test_chart_data_matches_category_totals(db_path, user_id):
    _expense(user_id, 80_000, "Hiburan", "2026-10-02")
    _expense(user_id, 120_000, "Kuliah", "2026-10-03")

    chart = chart_data_for_month(user_id, "2026-10")
    assert chart.labels == ["Kuliah", "Hiburan"]
    assert chart.values == [120_000.0, 80_000.0]


def test_resolve_analytics_month_prefers_explicit_and_latest(db_path, user_id):
    assert resolve_analytics_month(user_id, "2026-07") == "2026-07"
    _expense(user_id, 10_000, "Lainnya", "2025-12-15")
    assert resolve_analytics_month(user_id) == "2025-12"
