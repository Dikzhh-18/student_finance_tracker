from app.repositories.finance_repository import create_transaction, list_budget_records
from app.services.finance_service import (
    delete_budget_by_id,
    list_budget_progress,
    save_budget_payload,
    upsert_budget_payload,
)


def test_save_budget_payload_validates_inputs():
    payload, errors = save_budget_payload(category="", limit="-1")
    assert payload is None
    assert any("Kategori" in error for error in errors)
    assert any("Limit" in error for error in errors)


def test_save_budget_payload_parses_indonesian_amount():
    payload, errors = save_budget_payload(category="  Makan  ", limit="500.000")
    assert errors == []
    assert payload is not None
    assert payload.category == "Makan"
    assert payload.monthly_limit == 500_000


def test_upsert_and_progress_tracks_spent(db_path, user_id):
    payload, errors = save_budget_payload(category="Makan", limit="400000")
    assert payload is not None and errors == []
    upsert_budget_payload(user_id, payload)

    create_transaction(
        user_id=user_id,
        tx_type="expense",
        amount=250_000,
        category="Makan",
        description="Minggu 1",
        date="2026-03-04",
    )
    create_transaction(
        user_id=user_id,
        tx_type="expense",
        amount=50_000,
        category="Transport",
        description="Ojek",
        date="2026-03-05",
    )

    budgets = list_budget_progress(user_id, "2026-03")
    makan = next(item for item in budgets if item.category == "Makan")
    assert makan.spent == 250_000
    assert makan.remaining == 150_000
    assert makan.over_budget is False
    assert makan.percent == 62.5
    assert makan.bar_class == "bg-indigo-500"


def test_budget_over_limit_and_bar_class(db_path, user_id):
    payload, _ = save_budget_payload(category="Hiburan", limit="100000")
    upsert_budget_payload(user_id, payload)
    create_transaction(
        user_id=user_id,
        tx_type="expense",
        amount=150_000,
        category="Hiburan",
        description="Konser",
        date="2026-03-08",
    )

    hiburan = list_budget_progress(user_id, "2026-03")[0]
    assert hiburan.over_budget is True
    assert hiburan.percent == 100
    assert hiburan.raw_percent == 150
    assert hiburan.bar_class == "bg-rose-500"


def test_upsert_updates_same_category_and_delete(db_path, user_id):
    first, _ = save_budget_payload(category="Kos", limit="400000")
    upsert_budget_payload(user_id, first)
    second, _ = save_budget_payload(category="Kos", limit="550000")
    upsert_budget_payload(user_id, second)

    records = list_budget_records(user_id)
    assert len(records) == 1
    assert records[0]["monthly_limit"] == 550_000

    assert delete_budget_by_id(user_id, records[0]["id"]) is True
    assert list_budget_records(user_id) == []
    assert delete_budget_by_id(user_id, records[0]["id"]) is False
