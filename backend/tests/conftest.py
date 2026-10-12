import pytest
import re
from fastapi.testclient import TestClient

from app.repositories.finance_repository import create_user, get_user_by_email, init_db
from app.services.auth_service import hash_password
from main import app


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("app.config.DB_PATH", path)
    monkeypatch.setattr("app.repositories.finance_repository.DB_PATH", path)
    init_db(seed=False)
    create_user(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("test-password-123"),
    )
    return path


@pytest.fixture
def user_id(db_path):
    return get_user_by_email("test@example.com")["id"]


@pytest.fixture
def authenticated_client(db_path, user_id):
    with TestClient(app) as client:
        login_page = client.get("/login")
        csrf = re.search(
            r'name="csrf_token" value="([^"]+)"', login_page.text
        ).group(1)
        response = client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "email": "test@example.com",
                "password": "test-password-123",
                "next": "/",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        yield client
