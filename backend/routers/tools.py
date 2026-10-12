"""Utility routes: CSV export, database backup, restore."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse

from app.config import DB_PATH
from app.repositories.finance_repository import (
    _build_filters,
    get_connection,
    get_summary,
)
from app.services.dashboard_service import redirect_home
from app.utils.templates import templates

router = APIRouter(tags=["tools"])
BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


def csv_escape(value: str) -> str:
    if "," in value or '"' in value or "\n" in value:
        return '"' + value.replace('"', '""') + '"'
    return value


@router.get("/transactions/export")
def export_transactions_csv(
    request: Request,
    type: str | None = None,
    category: str | None = None,
    month: str | None = None,
    q: str | None = None,
):
    """Export filtered transactions to CSV."""
    where, params = _build_filters(
        tx_type=type, category=category, month=month, q=q
    )
    params.append(10_000)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, date, type, category, description, amount, created_at
            FROM transactions
            {where}
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["id", "tanggal", "tipe", "kategori", "keterangan", "jumlah", "dibuat"])
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["date"],
                row["type"],
                row["category"],
                row["description"],
                f"{row['amount']:,.2f}".replace(",", "."),
                row["created_at"],
            ]
        )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"transaksi_{timestamp}.csv"
    return StreamingResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
