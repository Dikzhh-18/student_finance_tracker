import re
from io import BytesIO

from PIL import Image

from fastapi.testclient import TestClient

from main import app
from app.repositories.finance_repository import create_transaction, get_transaction


def test_primary_navigation_pages_render(authenticated_client):
    pages = {
        "/": "Dashboard",
        "/transactions/new?type=expense": "Tambah pengeluaran",
        "/transactions/new?type=income": "Tambah pemasukan",
        "/analytics": "Grafik data",
        "/transactions": "Riwayat transaksi",
        "/account": "Akun & profil",
    }
    for path, heading in pages.items():
        response = authenticated_client.get(path)
        assert response.status_code == 200, path
        assert heading in response.text, path


def test_dashboard_renders_and_csrf_protected_form_posts(authenticated_client):
    response = authenticated_client.get("/")
    assert response.status_code == 200
    assert "Finance Tracker" in response.text
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)

    post_response = authenticated_client.post(
        "/transactions",
        data={
            "csrf_token": csrf,
            "type": "expense",
            "amount": "12500",
            "category": "Makan",
            "description": "Tes dashboard",
            "date": "2026-10-11",
        },
        follow_redirects=False,
    )
    assert post_response.status_code == 303


def test_invalid_transaction_renders_dedicated_form_page(authenticated_client):
    response = authenticated_client.get("/transactions/new?type=income")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
    invalid_response = authenticated_client.post(
        "/transactions",
        data={
            "csrf_token": csrf,
            "type": "income",
            "amount": "0",
            "category": "",
            "description": "",
            "date": "2026-10-11",
        },
    )
    assert invalid_response.status_code == 400
    assert "Tambah pemasukan" in invalid_response.text
    assert "Periksa input berikut" in invalid_response.text


def test_state_changing_request_without_csrf_token_is_rejected(authenticated_client):
    response = authenticated_client.post(
        "/transactions",
        data={"type": "expense", "amount": "12500", "category": "Makan", "date": "2026-10-11"},
    )
    assert response.status_code == 403


def test_state_changing_request_with_invalid_csrf_token_is_rejected(authenticated_client):
    response = authenticated_client.post(
        "/transactions",
        data={"csrf_token": "invalid-token", "type": "expense", "amount": "12500", "category": "Makan", "date": "2026-10-11"},
    )
    assert response.status_code == 403


def test_private_pages_redirect_to_login_without_session(db_path):
    with TestClient(app) as client:
        response = client.get("/transactions", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Ftransactions"


def test_registration_login_and_logout_cycle(db_path):
    with TestClient(app) as client:
        register_page = client.get("/register")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', register_page.text).group(1)
        registered = client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "New Account",
                "email": "new@example.com",
                "password": "another-password-123",
                "password_confirmation": "another-password-123",
            },
            follow_redirects=False,
        )
        assert registered.status_code == 303
        assert client.get("/").status_code == 200
        assert "New Account" in client.get("/account").text

        csrf = re.search(r'name="csrf_token" value="([^\"]+)"', client.get("/account").text).group(1)
        logged_out = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
        assert logged_out.status_code == 303
        assert client.get("/", follow_redirects=False).status_code == 303


def test_finance_routes_isolate_users_even_when_ids_are_guessed(
    authenticated_client, user_id
):
    transaction_id = create_transaction(
        user_id=user_id,
        tx_type="expense",
        amount=4321,
        category="Private category",
        description="Owner-only row",
        date="2026-10-11",
    )
    assert "Private category" in authenticated_client.get("/transactions").text

    csrf = re.search(
        r'name="csrf_token" value="([^\"]+)"',
        authenticated_client.get("/account").text,
    ).group(1)
    authenticated_client.post("/logout", data={"csrf_token": csrf})

    register_page = authenticated_client.get("/register")
    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', register_page.text).group(1)
    authenticated_client.post(
        "/register",
        data={
            "csrf_token": csrf,
            "name": "Second User",
            "email": "second@example.com",
            "password": "second-password-123",
            "password_confirmation": "second-password-123",
        },
    )

    history = authenticated_client.get("/transactions")
    assert history.status_code == 200
    assert "Private category" not in history.text
    account_page = authenticated_client.get("/account")
    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', account_page.text).group(1)
    forged_delete = authenticated_client.post(
        f"/transactions/{transaction_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert forged_delete.status_code == 303
    assert get_transaction(user_id, transaction_id) is not None


def test_profile_edit_and_theme_preference_are_persisted(authenticated_client, user_id):
    response = authenticated_client.get("/account")
    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', response.text).group(1)
    profile = authenticated_client.post(
        "/account/profile",
        data={"csrf_token": csrf, "name": "Updated User", "email": "updated@example.com"},
        follow_redirects=False,
    )
    assert profile.status_code == 303
    assert "Updated User" in authenticated_client.get("/account").text

    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', authenticated_client.get("/account").text).group(1)
    theme = authenticated_client.post(
        "/account/theme",
        data={"csrf_token": csrf, "theme": "dark"},
        follow_redirects=False,
    )
    assert theme.status_code == 303
    page = authenticated_client.get("/account")
    assert 'data-theme="dark"' in page.text
    assert "Gelap" in page.text

    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', page.text).group(1)
    authenticated_client.post("/logout", data={"csrf_token": csrf})
    login_page = authenticated_client.get("/login")
    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', login_page.text).group(1)
    logged_in = authenticated_client.post(
        "/login",
        data={
            "csrf_token": csrf,
            "email": "updated@example.com",
            "password": "test-password-123",
            "next": "/",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 303
    assert 'data-theme="dark"' in authenticated_client.get("/").text


def test_avatar_upload_is_validated_stored_and_served_privately(authenticated_client, user_id):
    image = Image.new("RGB", (32, 24), color=(40, 100, 180))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    csrf = re.search(
        r'name="csrf_token" value="([^\"]+)"',
        authenticated_client.get("/account").text,
    ).group(1)
    upload = authenticated_client.post(
        "/account/avatar",
        data={"csrf_token": csrf},
        files={"avatar": ("avatar.png", buffer.getvalue(), "image/png")},
        follow_redirects=False,
    )
    assert upload.status_code == 303

    avatar = authenticated_client.get("/account/avatar")
    assert avatar.status_code == 200
    assert avatar.headers["content-type"] == "image/jpeg"
    assert avatar.headers["x-content-type-options"] == "nosniff"
    assert Image.open(BytesIO(avatar.content)).format == "JPEG"


def test_invalid_avatar_is_rejected(authenticated_client):
    csrf = re.search(
        r'name="csrf_token" value="([^\"]+)"',
        authenticated_client.get("/account").text,
    ).group(1)
    response = authenticated_client.post(
        "/account/avatar",
        data={"csrf_token": csrf},
        files={"avatar": ("not-image.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400
    assert "bukan gambar yang valid" in response.text


def test_avatar_route_does_not_expose_other_accounts_photo(
    authenticated_client, user_id
):
    image = Image.new("RGB", (16, 16), color=(180, 80, 40))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', authenticated_client.get("/account").text).group(1)
    authenticated_client.post(
        "/account/avatar",
        data={"csrf_token": csrf},
        files={"avatar": ("private.jpg", buffer.getvalue(), "image/jpeg")},
    )

    authenticated_client.post("/logout", data={"csrf_token": csrf})
    register_page = authenticated_client.get("/register")
    csrf = re.search(r'name="csrf_token" value="([^\"]+)"', register_page.text).group(1)
    authenticated_client.post(
        "/register",
        data={
            "csrf_token": csrf,
            "name": "No Photo User",
            "email": "no-photo@example.com",
            "password": "no-photo-password-123",
            "password_confirmation": "no-photo-password-123",
        },
    )
    assert authenticated_client.get("/account/avatar").status_code == 404


def test_avatar_upload_rejects_files_over_limit(authenticated_client):
    csrf = re.search(
        r'name="csrf_token" value="([^\"]+)"',
        authenticated_client.get("/account").text,
    ).group(1)
    response = authenticated_client.post(
        "/account/avatar",
        data={"csrf_token": csrf},
        files={"avatar": ("too-large.png", b"x" * (2 * 1024 * 1024 + 10), "image/png")},
    )
    assert response.status_code == 400
    assert "maksimal 2 MB" in response.text


def test_theme_endpoint_rejects_unknown_theme(authenticated_client):
    response = authenticated_client.post(
        "/account/theme/select",
        data={"csrf_token": re.search(
            r'name="csrf_token" value="([^\"]+)"',
            authenticated_client.get("/account").text,
        ).group(1), "theme": "neon"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Pilihan tema tidak valid" in response.text
