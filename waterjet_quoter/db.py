"""Postgres connection boundary (Supabase-hosted `materials` table).

The only thing downstream code should import from here is get_connection().
Nothing else in the codebase should know how or where the connection
string is stored -- that keeps the materials data source swappable, the
same way ingestion.py isolates the DXF file source.
"""
import os
from pathlib import Path
from typing import Optional

import psycopg
from dotenv import load_dotenv

load_dotenv()

DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when no usable DATABASE_URL can be found."""


def _bare_url_from_dotenv_file(path: Path) -> Optional[str]:
    """Fallback for a .env saved with a bare connection string and no
    DATABASE_URL= key -- this has happened repeatedly with manually edited
    .env files, so tolerate it instead of failing every time.
    """
    if not path.exists():
        return None
    content = path.read_text().strip()
    if content.startswith("postgres://") or content.startswith("postgresql://"):
        return content
    return None


def _resolve_database_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or _bare_url_from_dotenv_file(DOTENV_PATH)


def get_connection() -> psycopg.Connection:
    database_url = _resolve_database_url()
    if not database_url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL n'est pas défini. Crée un fichier .env à la racine "
            "du projet avec DATABASE_URL=postgresql://... (voir Supabase -> "
            "Project Settings -> Database -> Connection string -> URI)."
        )
    return psycopg.connect(database_url)
