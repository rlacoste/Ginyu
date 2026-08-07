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


def test_sheet_cost_by_material_has_required_materials():
    for material in ("aluminum", "mild_steel", "stainless_steel"):
        assert material in config.SHEET_COST_BY_MATERIAL
        assert config.SHEET_COST_BY_MATERIAL[material] > 0


def test_labor_flat_fees_has_required_categories():
    for category in ("programming", "setup", "shipping"):
        assert category in config.LABOR_FLAT_FEES
        assert config.LABOR_FLAT_FEES[category] >= 0


def test_pierce_time_calibration_constant_is_positive():
    assert config.PIERCE_TIME_CALIBRATION_CONSTANT > 0
