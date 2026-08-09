import pytest

from waterjet_quoter.db import _resolve_database_url
from waterjet_quoter.materials import MaterialNotFoundError
from waterjet_quoter.material_prices import (
    _rows_to_price_table,
    lookup_price,
    load_price_table,
)


def test_rows_to_price_table_builds_structure():
    rows = [
        ("Aluminium", 1.85, 1.0),
        ("Copper", 4.50, 2.0),
    ]

    table = _rows_to_price_table(rows)

    assert table["Aluminium"]["price_per_lb"] == 1.85
    assert table["Aluminium"]["machine_rate_multiplier"] == 1.0
    assert table["Copper"]["price_per_lb"] == 4.50
    assert table["Copper"]["machine_rate_multiplier"] == 2.0


def test_lookup_price_returns_params():
    table = {"Aluminium": {"price_per_lb": 1.85, "machine_rate_multiplier": 1.0}}

    params = lookup_price("Aluminium", table=table)

    assert params.price_per_lb == 1.85
    assert params.machine_rate_multiplier == 1.0


def test_lookup_price_raises_for_unknown_material():
    table = {"Aluminium": {"price_per_lb": 1.85, "machine_rate_multiplier": 1.0}}

    with pytest.raises(MaterialNotFoundError) as exc_info:
        lookup_price("Titanium", table=table)

    message = str(exc_info.value)
    assert "Titanium" in message
    assert not message.startswith('"')
    assert not message.endswith('"')


@pytest.mark.skipif(
    not _resolve_database_url(),
    reason="DATABASE_URL not configured -- requires a live Supabase connection",
)
def test_load_price_table_from_real_database():
    table = load_price_table()
    assert isinstance(table, dict)
