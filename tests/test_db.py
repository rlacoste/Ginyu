import pytest

from waterjet_quoter import db
from waterjet_quoter.db import (
    DatabaseNotConfiguredError,
    _bare_url_from_dotenv_file,
    _resolve_database_url,
    get_connection,
)


def test_get_connection_raises_clear_error_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db, "DOTENV_PATH", db.DOTENV_PATH.parent / "does-not-exist.env")

    with pytest.raises(DatabaseNotConfiguredError):
        get_connection()


def test_bare_url_from_dotenv_file_returns_none_when_file_missing(tmp_path):
    assert _bare_url_from_dotenv_file(tmp_path / "missing.env") is None


def test_bare_url_from_dotenv_file_returns_none_for_proper_key_value(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("DATABASE_URL=postgresql://user:pw@host:5432/db\n")

    assert _bare_url_from_dotenv_file(env_path) is None


def test_bare_url_from_dotenv_file_returns_url_for_bare_content(tmp_path):
    """Regression: a .env saved with just the raw connection string and no
    DATABASE_URL= key -- this has happened repeatedly with manually edited
    .env files -- must still work instead of silently failing every time.
    """
    env_path = tmp_path / ".env"
    env_path.write_text("postgresql://user:pw@host:5432/db\n")

    assert _bare_url_from_dotenv_file(env_path) == "postgresql://user:pw@host:5432/db"


def test_resolve_database_url_prefers_environment_variable(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("postgresql://from-file:pw@host:5432/db\n")
    monkeypatch.setattr(db, "DOTENV_PATH", env_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://from-env:pw@host:5432/db")

    assert _resolve_database_url() == "postgresql://from-env:pw@host:5432/db"


def test_resolve_database_url_falls_back_to_bare_dotenv_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("postgresql://from-file:pw@host:5432/db\n")
    monkeypatch.setattr(db, "DOTENV_PATH", env_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert _resolve_database_url() == "postgresql://from-file:pw@host:5432/db"
