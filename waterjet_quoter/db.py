"""Postgres connection boundary (Supabase-hosted `materials` table).

The only thing downstream code should import from here is get_connection().
Nothing else in the codebase should know how or where the connection
string is stored -- that keeps the materials data source swappable, the
same way ingestion.py isolates the DXF file source.
"""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when DATABASE_URL is not set in the environment."""


def get_connection() -> psycopg.Connection:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL n'est pas défini. Crée un fichier .env à la racine "
            "du projet avec DATABASE_URL=postgresql://... (voir Supabase -> "
            "Project Settings -> Database -> Connection string -> URI)."
        )
    return psycopg.connect(database_url)
