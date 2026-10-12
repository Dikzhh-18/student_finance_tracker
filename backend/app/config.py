"""Shared application configuration values."""

from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DB_PATH = PROJECT_ROOT / "finance.db"

ALLOWED_TYPES = {"income", "expense"}

INCOME_CATEGORIES = (
    "Beasiswa",
    "Orang Tua",
    "Kerja",
    "Lainnya",
)

EXPENSE_CATEGORIES = (
    "Kos",
    "Makan",
    "Transport",
    "Kuliah",
    "Hiburan",
    "Kebutuhan",
    "Lainnya",
)

DEFAULT_CATEGORIES = tuple(
    dict.fromkeys([*INCOME_CATEGORIES, *EXPENSE_CATEGORIES])
)

MONTH_NAMES_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}
