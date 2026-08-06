import math

import pytest

from waterjet_quoter.geometry import Contour, Piece
from waterjet_quoter.costing import estimate_material
from waterjet_quoter import config


def test_estimate_material_computes_sheets_needed():
    piece = Piece(
        piece_id=0,
        contours=[Contour(points=[(0, 0), (10, 0), (10, 6), (0, 6), (0, 0)])],
    )

    result = estimate_material([piece], quantity=50)

    expected_total_area = 60.0 * 50
    sheet_area = config.SHEET_WIDTH_IN * config.SHEET_HEIGHT_IN
    usable_area = sheet_area * config.NESTING_UTILIZATION_FACTOR
    expected_sheets = math.ceil(expected_total_area / usable_area)

    assert result.total_area_in2 == pytest.approx(expected_total_area)
    assert result.sheets_needed == expected_sheets
    assert result.utilization_factor == config.NESTING_UTILIZATION_FACTOR
    assert result.warnings == []


def test_estimate_material_flags_large_piece():
    large_piece = Piece(
        piece_id=0,
        contours=[Contour(points=[(0, 0), (50, 0), (50, 20), (0, 20), (0, 0)])],
    )

    result = estimate_material([large_piece], quantity=1)

    assert len(result.warnings) == 1
    assert "nesting manuel recommandé" in result.warnings[0]


def test_estimate_material_zero_pieces_needs_zero_sheets():
    result = estimate_material([], quantity=1)
    assert result.total_area_in2 == 0.0
    assert result.sheets_needed == 0
