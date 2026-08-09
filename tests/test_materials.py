import pytest

from waterjet_quoter.db import _resolve_database_url
from waterjet_quoter.materials import (
    MaterialNotFoundError,
    _rows_to_table,
    lookup,
    load_table,
)


def test_rows_to_table_builds_nested_structure():
    rows = [
        ("Aluminium", "6061 T6", 0.25, 90.424),
        ("Aluminium", "6061 T6", 1.0, 18.288),
        ("Mild Steel", "A1008", 0.125, 60.0),
    ]

    table = _rows_to_table(rows)

    assert table["Aluminium"][0.25]["6061 T6"]["feed_rate_ipm"] == 90.424
    assert table["Aluminium"][1.0]["6061 T6"]["feed_rate_ipm"] == 18.288
    assert table["Mild Steel"][0.125]["A1008"]["feed_rate_ipm"] == 60.0


def test_rows_to_table_normalizes_thickness_precision():
    rows = [("Aluminium", "6061 T6", 0.250000001, 90.0)]

    table = _rows_to_table(rows)

    assert 0.25 in table["Aluminium"]


def test_lookup_returns_feed_rate():
    table = {"Aluminium": {0.25: {"6061 T6": {"feed_rate_ipm": 100.0}}}}

    params = lookup("Aluminium", 0.25, "6061 T6", table=table)

    assert params.feed_rate_ipm == 100.0


def test_lookup_normalizes_thickness_for_matching():
    table = {"Aluminium": {0.25: {"6061 T6": {"feed_rate_ipm": 100.0}}}}

    params = lookup("Aluminium", 0.2500001, "6061 T6", table=table)

    assert params.feed_rate_ipm == 100.0


def test_lookup_raises_for_unknown_material():
    table = {"Aluminium": {0.25: {"6061 T6": {"feed_rate_ipm": 100.0}}}}

    with pytest.raises(MaterialNotFoundError):
        lookup("Titanium", 0.25, "6061 T6", table=table)


def test_lookup_raises_for_unknown_thickness_and_lists_available():
    table = {
        "Aluminium": {
            0.25: {"6061 T6": {"feed_rate_ipm": 100.0}},
            1.0: {"6061 T6": {"feed_rate_ipm": 18.0}},
        }
    }

    with pytest.raises(MaterialNotFoundError) as exc_info:
        lookup("Aluminium", 0.5, "6061 T6", table=table)

    message = str(exc_info.value)
    assert "0.25" in message and "1.0" in message


def test_lookup_raises_for_unknown_quality_and_lists_available():
    table = {
        "Aluminium": {
            0.25: {
                "6061 T6": {"feed_rate_ipm": 100.0},
                "5052": {"feed_rate_ipm": 95.0},
            }
        }
    }

    with pytest.raises(MaterialNotFoundError) as exc_info:
        lookup("Aluminium", 0.25, "3003", table=table)

    message = str(exc_info.value)
    assert "6061 T6" in message and "5052" in message


def test_material_not_found_error_str_has_no_stray_quotes():
    table = {"Aluminium": {0.25: {"6061 T6": {"feed_rate_ipm": 100.0}}}}

    with pytest.raises(MaterialNotFoundError) as exc_info:
        lookup("Titanium", 0.25, "6061 T6", table=table)

    message = str(exc_info.value)
    assert not message.startswith('"')
    assert not message.endswith('"')


@pytest.mark.skipif(
    not _resolve_database_url(),
    reason="DATABASE_URL not configured -- requires a live Supabase connection",
)
def test_load_table_from_real_database_has_entries():
    table = load_table()
    assert len(table) > 0
