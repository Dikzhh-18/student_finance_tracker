import os

from sqlalchemy import create_engine


def test_mysql_driver_is_available_without_opening_a_connection(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://finance_user:placeholder@127.0.0.1:3306/student_finance?charset=utf8mb4",
    )
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        assert engine.dialect.name == "mysql"
        assert engine.dialect.driver == "pymysql"
    finally:
        engine.dispose()


def test_supabase_postgresql_url_uses_psycopg_and_small_serverless_pool(monkeypatch):
    from app.repositories.finance_repository import _database_url, _engine_for

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres.project:placeholder@pooler.supabase.com:6543/postgres?sslmode=require",
    )
    url = _database_url()
    assert url.startswith("postgresql+psycopg://")

    engine = _engine_for(url)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.pool.size() == 1
        assert engine.pool._max_overflow == 0
    finally:
        engine.dispose()
