import pytest

from waterjet_quoter.db import DatabaseNotConfiguredError, get_connection


def test_get_connection_raises_clear_error_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(DatabaseNotConfiguredError):
        get_connection()
