"""Account registration and password verification helpers."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.repositories.finance_repository import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_avatar,
    update_user_profile,
    update_user_theme,
)

_ITERATIONS = 600_000
MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_AVATAR_DIMENSION = 512
Image.MAX_IMAGE_PIXELS = 20_000_000


class RegistrationError(ValueError):
    """Raised when the requested account cannot be registered."""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def register_account(*, name: str, email: str, password: str) -> int:
    normalized_name = name.strip()
    normalized_email = email.strip().lower()
    if not normalized_name or len(normalized_name) > 100:
        raise RegistrationError("Nama wajib diisi (maksimal 100 karakter).")
    if len(normalized_email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise RegistrationError("Alamat email tidak valid.")
    if len(password) < 10 or len(password) > 256:
        raise RegistrationError("Kata sandi harus terdiri dari 10 sampai 256 karakter.")
    if get_user_by_email(normalized_email):
        raise RegistrationError("Email tersebut sudah terdaftar.")
    return create_user(
        name=normalized_name,
        email=normalized_email,
        password_hash=hash_password(password),
    )


def authenticate_account(*, email: str, password: str) -> dict | None:
    user = get_user_by_email(email.strip().lower())
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "theme": user.get("theme", "light"),
        "has_avatar": bool(user.get("has_avatar", False)),
    }


def get_account_by_id(user_id: int) -> dict | None:
    return get_user_by_id(user_id)


def update_profile(*, user_id: int, name: str, email: str) -> tuple[str, str]:
    normalized_name = name.strip()
    normalized_email = email.strip().lower()
    if not normalized_name or len(normalized_name) > 100:
        raise RegistrationError("Nama wajib diisi (maksimal 100 karakter).")
    if len(normalized_email) > 254 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email
    ):
        raise RegistrationError("Alamat email tidak valid.")
    existing = get_user_by_email(normalized_email)
    if existing and existing["id"] != user_id:
        raise RegistrationError("Email tersebut sudah digunakan akun lain.")
    update_user_profile(user_id=user_id, name=normalized_name, email=normalized_email)
    return normalized_name, normalized_email


def save_theme(*, user_id: int, theme: str) -> str:
    if theme not in {"light", "dark"}:
        raise RegistrationError("Pilihan tema tidak valid.")
    update_user_theme(user_id=user_id, theme=theme)
    return theme


def normalize_avatar(raw: bytes) -> tuple[bytes, str]:
    if not raw:
        raise RegistrationError("Pilih foto terlebih dahulu.")
    if len(raw) > MAX_AVATAR_BYTES:
        raise RegistrationError("Ukuran foto maksimal 2 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise RegistrationError("Gunakan foto JPEG, PNG, atau WebP.")
                source.verify()
            with Image.open(BytesIO(raw)) as source:
                source = ImageOps.exif_transpose(source)
                source.thumbnail((MAX_AVATAR_DIMENSION, MAX_AVATAR_DIMENSION))
                if source.mode in {"RGBA", "LA"}:
                    background = Image.new("RGB", source.size, "white")
                    background.paste(source, mask=source.getchannel("A"))
                    source = background
                else:
                    source = source.convert("RGB")
                output = BytesIO()
                source.save(output, format="JPEG", quality=86, optimize=True)
                return output.getvalue(), "image/jpeg"
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise RegistrationError("File yang diunggah bukan gambar yang valid.") from exc


def save_avatar(*, user_id: int, raw: bytes) -> None:
    image, content_type = normalize_avatar(raw)
    update_user_avatar(user_id=user_id, image=image, content_type=content_type)


def remove_avatar(*, user_id: int) -> None:
    update_user_avatar(user_id=user_id, image=None, content_type=None)
