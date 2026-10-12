"""Import the former single-user SQLite data into a PostgreSQL/MySQL account.

Run from the project root after setting DATABASE_URL and SESSION_SECRET_KEY:
    python backend/migrate_sqlite_to_database.py --owner-email you@example.com
"""

from __future__ import annotations

import argparse
import os
import sqlite3

from sqlalchemy import text

from app.repositories.finance_repository import get_user_by_email, get_connection, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", default="finance.db", help="Path to the legacy SQLite file")
    parser.add_argument("--owner-email", required=True, help="Existing target account that will own imported data")
    args = parser.parse_args()

    target_url = os.getenv("DATABASE_URL", "")
    if not target_url.startswith(("mysql", "postgres://", "postgresql://", "postgresql+psycopg://")):
        raise SystemExit("Set DATABASE_URL to a MySQL or PostgreSQL connection URL before running this import.")
    init_db(seed=False)
    user = get_user_by_email(args.owner_email.strip().lower())
    if user is None:
        raise SystemExit("The owner account does not exist in the target database; register it first.")

    with sqlite3.connect(args.sqlite_path) as source:
        source.row_factory = sqlite3.Row
        tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"transactions", "budgets"}.issubset(tables):
            raise SystemExit("SQLite source must contain transactions and budgets tables.")
        if "users" in tables and source.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise SystemExit(
                "This importer only accepts the former single-user SQLite database. "
                "The source now has accounts; refusing to merge users' private data."
            )
        transaction_columns = {row[1] for row in source.execute("PRAGMA table_info(transactions)")}
        budget_columns = {row[1] for row in source.execute("PRAGMA table_info(budgets)")}
        if "user_id" in transaction_columns and source.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id IS NOT NULL"
        ).fetchone()[0]:
            raise SystemExit("SQLite transactions already belong to accounts; refusing a single-owner import.")
        if "user_id" in budget_columns and source.execute(
            "SELECT COUNT(*) FROM budgets WHERE user_id IS NOT NULL"
        ).fetchone()[0]:
            raise SystemExit("SQLite budgets already belong to accounts; refusing a single-owner import.")
        transactions = [dict(row) for row in source.execute("SELECT id, type, amount, category, description, date, created_at FROM transactions")]
        budgets = [dict(row) for row in source.execute("SELECT id, category, monthly_limit, created_at FROM budgets")]

    with get_connection() as target:
        existing = target.execute(
            text("SELECT (SELECT COUNT(*) FROM transactions WHERE user_id=:id) + (SELECT COUNT(*) FROM budgets WHERE user_id=:id)"),
            {"id": user["id"]},
        ).scalar_one()
        if existing:
            raise SystemExit("Target account already has finance data; refusing to risk duplicate import.")
        if transactions:
            target.execute(text("""
                INSERT INTO transactions (user_id, type, amount, category, description, date, created_at)
                VALUES (:user_id, :type, :amount, :category, :description, :date, :created_at)
            """), [dict(row, user_id=user["id"]) for row in transactions])
        if budgets:
            target.execute(text("""
                INSERT INTO budgets (user_id, category, monthly_limit, created_at)
                VALUES (:user_id, :category, :monthly_limit, :created_at)
            """), [dict(row, user_id=user["id"]) for row in budgets])

    print(f"Imported {len(transactions)} transactions and {len(budgets)} budgets for {user['email']}.")


if __name__ == "__main__":
    main()
