from waterjet_quoter import config


def test_nesting_utilization_factor_default():
    assert config.NESTING_UTILIZATION_FACTOR == 0.75


def test_sheet_dimensions():
    assert config.SHEET_WIDTH_IN == 48.0
    assert config.SHEET_HEIGHT_IN == 96.0


def test_large_piece_threshold():
    assert config.LARGE_PIECE_DIMENSION_THRESHOLD_IN == 40.0


def test_machine_rate_default():
    assert config.MACHINE_RATE_PER_HOUR == 125.0


def test_density_has_required_materials():
    # Keys must match the `material` column values in the Postgres
    # materials/material_prices tables (iGEMS naming), not an invented slug
    # -- otherwise compute_price() can't find a density for a material
    # lookup() just successfully resolved.
    for material in ("Aluminium", "Mild Steel", "Stainless Steel", "Copper"):
        assert material in config.DENSITY_KG_PER_M3
        assert config.DENSITY_KG_PER_M3[material] > 0


def test_material_cost_adjustment_factor_is_positive():
    assert config.MATERIAL_COST_ADJUSTMENT_FACTOR > 0


def test_labor_flat_fees_has_required_categories():
    for category in ("programming", "setup", "shipping"):
        assert category in config.LABOR_FLAT_FEES
        assert config.LABOR_FLAT_FEES[category] >= 0
