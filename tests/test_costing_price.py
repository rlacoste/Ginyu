import pytest

from waterjet_quoter.costing import compute_price, KG_PER_M3_TO_LB_PER_IN3
from waterjet_quoter import config
from waterjet_quoter.materials import MaterialNotFoundError

PRICE_TABLE = {
    "Aluminium": {"price_per_lb": 1.85, "machine_rate_multiplier": 1.0},
    "Copper": {"price_per_lb": 4.50, "machine_rate_multiplier": 2.0},
}


def test_compute_price_breaks_down_components():
    result = compute_price(
        total_time_min=120.0,
        net_area_in2=100.0,
        thickness_in=0.25,
        material="Aluminium",
        price_table=PRICE_TABLE,
    )

    expected_machine_cost = (120.0 / 60.0) * config.MACHINE_RATE_PER_HOUR * 1.0
    density_lb_per_in3 = config.DENSITY_KG_PER_M3["Aluminium"] * KG_PER_M3_TO_LB_PER_IN3
    expected_weight_lb = 100.0 * 0.25 * density_lb_per_in3
    expected_material_cost = (
        expected_weight_lb * 1.85 * config.MATERIAL_COST_ADJUSTMENT_FACTOR
    )
    expected_labor_cost = sum(config.LABOR_FLAT_FEES.values())

    assert result.machine_time_cost == pytest.approx(expected_machine_cost)
    assert result.material_cost == pytest.approx(expected_material_cost)
    assert result.labor_cost == pytest.approx(expected_labor_cost)
    assert result.total_price == pytest.approx(
        expected_machine_cost + expected_material_cost + expected_labor_cost
    )


def test_compute_price_applies_machine_rate_multiplier():
    result = compute_price(
        total_time_min=60.0,
        net_area_in2=10.0,
        thickness_in=0.1,
        material="Copper",
        price_table=PRICE_TABLE,
    )

    expected_machine_cost = (60.0 / 60.0) * config.MACHINE_RATE_PER_HOUR * 2.0
    assert result.machine_time_cost == pytest.approx(expected_machine_cost)


def test_compute_price_raises_for_material_missing_density():
    with pytest.raises(MaterialNotFoundError) as exc_info:
        compute_price(
            total_time_min=60.0,
            net_area_in2=10.0,
            thickness_in=0.1,
            material="Unobtainium",
            price_table=PRICE_TABLE,
        )

    message = str(exc_info.value)
    assert not message.startswith('"')
    assert "Unobtainium" in message


def test_compute_price_raises_for_material_missing_price():
    with pytest.raises(MaterialNotFoundError) as exc_info:
        compute_price(
            total_time_min=60.0,
            net_area_in2=10.0,
            thickness_in=0.1,
            material="Aluminium",
            price_table={},  # no price configured
        )

    message = str(exc_info.value)
    assert not message.startswith('"')
    assert "Aluminium" in message
