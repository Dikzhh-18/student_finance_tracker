import sqlite3

from app.repositories import finance_repository as repo


def test_upgrades_single_user_sqlite_and_assigns_legacy_data_once(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL CHECK(monthly_limit > 0),
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            INSERT INTO transactions (type, amount, category, description, date)
            VALUES ('income', 123456, 'Beasiswa', 'Data lama', '2026-10-01');
            INSERT INTO budgets (category, monthly_limit) VALUES ('Makan', 250000);
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(254) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            INSERT INTO users (name, email, password_hash)
            VALUES ('Legacy Owner', 'legacy-owner@example.com', 'hash');
        """)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(repo, "DB_PATH", path)
    repo.init_db(seed=False)
    legacy_user = repo.get_user_by_email("legacy-owner@example.com")
    assert legacy_user["theme"] == "light"
    assert repo.get_user_by_id(legacy_user["id"])["has_avatar"] == 0

    user_id = repo.create_user(
        name="New Owner",
        email="new-owner@example.com",
        password_hash="not-used-in-this-test",
    )
    repo.init_db(seed=False)

    assert repo.get_summary(user_id)["total_income"] == 123456
    transactions = repo.list_transactions(user_id=user_id)
    assert len(transactions) == 1
    assert transactions[0]["description"] == "Data lama"
    assert len(repo.list_budget_records(user_id)) == 1
