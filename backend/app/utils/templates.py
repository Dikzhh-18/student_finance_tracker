"""Shared Jinja2 templates instance."""

import json

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.config import FRONTEND_DIR

templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")
templates.env.filters["tojson"] = lambda value: Markup(
    json.dumps(value, ensure_ascii=False)
)
