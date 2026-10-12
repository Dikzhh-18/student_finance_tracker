from app.repositories.finance_repository import (
    create_transaction,
    create_user,
    delete_budget,
    delete_transaction,
    get_summary,
    get_transaction,
    list_budget_records,
    list_transactions,
    update_transaction,
    upsert_budget,
)


def test_users_cannot_read_or_mutate_each_others_finance_data(db_path, user_id):
    other_id = create_user(
        name="Other User",
        email="other@example.com",
        password_hash="test-hash",
    )
    transaction_id = create_transaction(
        user_id=user_id,
        tx_type="income",
        amount=1_250_000,
        category="Beasiswa",
        description="Private income",
        date="2026-10-01",
    )
    upsert_budget(user_id=user_id, category="Makan", monthly_limit=300_000)
    upsert_budget(user_id=other_id, category="Makan", monthly_limit=900_000)

    assert len(list_transactions(user_id=user_id)) == 1
    assert list_transactions(user_id=other_id) == []
    assert get_summary(user_id)["total_income"] == 1_250_000
    assert get_summary(other_id)["total_income"] == 0
    assert get_transaction(other_id, transaction_id) is None
    assert update_transaction(
        other_id,
        transaction_id,
        tx_type="expense",
        amount=1,
        category="Changed",
        description="Unauthorized",
        date="2026-10-01",
    ) is False
    assert delete_transaction(other_id, transaction_id) is False

    first_budget, other_budget = list_budget_records(user_id), list_budget_records(other_id)
    assert first_budget[0]["monthly_limit"] == 300_000
    assert other_budget[0]["monthly_limit"] == 900_000
    assert delete_budget(other_id, first_budget[0]["id"]) is False
    assert len(list_budget_records(user_id)) == 1
