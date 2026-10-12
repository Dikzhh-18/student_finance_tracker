from app.schemas import TransactionCreate
from app.services.finance_service import create_new_transaction
from app.utils.validators import parse_amount, validate_transaction


def test_parse_amount_handles_indonesian_format():
    assert parse_amount("1.500.000") == 1500000.0
    assert parse_amount("1.500.000,50") == 1500000.5
    assert parse_amount("25000") == 25000.0


def test_validate_transaction_rejects_invalid_inputs():
    payload, errors = validate_transaction(
        tx_type="expense",
        amount_raw="-10",
        category="",
        description="",
        date_raw="2026-10-99",
    )

    assert payload is None
    assert any("Jumlah" in error for error in errors)
    assert any("Kategori" in error for error in errors)
    assert any("Tanggal" in error for error in errors)


def test_pydantic_transaction_schema_accepts_form_values():
    model = TransactionCreate.model_validate(
        {
            "type": "income",
            "amount": "1.250.000",
            "category": " Beasiswa ",
            "description": "cair",
            "date": "2026-03-01",
        }
    )
    assert model.amount == 1_250_000
    assert model.category == "Beasiswa"
    assert model.to_repo()["tx_type"] == "income"


def test_create_new_transaction_uses_schema_errors():
    payload, errors = create_new_transaction(
        tx_type="gift",
        amount="abc",
        category="",
        description="",
        date="bukan-tanggal",
    )
    assert payload is None
    assert any("Tipe" in error for error in errors)
    assert any("Jumlah" in error for error in errors)
