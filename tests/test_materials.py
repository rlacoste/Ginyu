# tests/test_materials.py
import pytest

from waterjet_quoter.materials import (
    MaterialNotFoundError,
    lookup,
    load_table,
)

REQUIRED_COMBOS = [
    ("aluminum", "6mm"),
    ("aluminum", "12mm"),
    ("mild_steel", "6mm"),
    ("mild_steel", "12mm"),
    ("stainless_steel", "6mm"),
    ("stainless_steel", "12mm"),
]


def test_shipped_table_has_all_required_combos():
    table = load_table()
    for material, thickness in REQUIRED_COMBOS:
        params = lookup(material, thickness, table=table)
        assert params.feed_rate_ipm > 0
        assert params.pierce_time_sec > 0


def test_lookup_default_quality_is_standard():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    params = lookup("aluminum", "6mm", table=table)
    assert params.feed_rate_ipm == 18.0
    assert params.pierce_time_sec == 3.0


def test_lookup_raises_for_unknown_material():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    with pytest.raises(MaterialNotFoundError):
        lookup("titanium", "6mm", table=table)


def test_lookup_raises_for_unknown_thickness():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    with pytest.raises(MaterialNotFoundError):
        lookup("aluminum", "20mm", table=table)


def test_lookup_raises_for_unknown_quality():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    with pytest.raises(MaterialNotFoundError):
        lookup("aluminum", "6mm", quality="fine", table=table)
