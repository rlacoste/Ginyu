import pytest

from waterjet_quoter.costing import compute_price
from waterjet_quoter import config


def test_compute_price_breaks_down_components():
    result = compute_price(total_time_min=120.0, sheets_needed=3, material="aluminum")

    expected_machine_cost = (120.0 / 60.0) * config.MACHINE_RATE_PER_HOUR
    expected_material_cost = 3 * config.SHEET_COST_BY_MATERIAL["aluminum"]
    expected_labor_cost = sum(config.LABOR_FLAT_FEES.values())

    assert result.machine_time_cost == pytest.approx(expected_machine_cost)
    assert result.material_cost == pytest.approx(expected_material_cost)
    assert result.labor_cost == pytest.approx(expected_labor_cost)
    assert result.total_price == pytest.approx(
        expected_machine_cost + expected_material_cost + expected_labor_cost
    )


def test_compute_price_raises_for_unknown_material():
    with pytest.raises(KeyError):
        compute_price(total_time_min=60.0, sheets_needed=1, material="titanium")
