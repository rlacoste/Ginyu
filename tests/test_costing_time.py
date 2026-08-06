# tests/test_costing_time.py
import pytest

from waterjet_quoter.geometry import Contour, Piece
from waterjet_quoter.materials import MaterialParams
from waterjet_quoter.costing import compute_cutting_time


def test_compute_cutting_time_single_piece():
    piece = Piece(
        piece_id=0,
        contours=[Contour(points=[(0, 0), (10, 0), (10, 6), (0, 6), (0, 0)])],
    )
    material = MaterialParams(feed_rate_ipm=10.0, pierce_time_sec=5.0)

    result = compute_cutting_time([piece], material, quantity=3)

    assert len(result.pieces) == 1
    quote = result.pieces[0]
    expected_unit_time = (32.0 / 10.0) + (1 * 5.0 / 60.0)
    assert quote.unit_time_min == pytest.approx(expected_unit_time)
    assert quote.cut_length_in == pytest.approx(32.0)
    assert quote.pierce_count == 1
    assert quote.bbox_width_in == pytest.approx(10.0)
    assert quote.bbox_height_in == pytest.approx(6.0)
    assert result.total_time_min == pytest.approx(expected_unit_time * 3)


def test_compute_cutting_time_accounts_for_multiple_pierces():
    piece = Piece(
        piece_id=0,
        contours=[
            Contour(points=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
            Contour(points=[(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)]),
        ],
    )
    material = MaterialParams(feed_rate_ipm=20.0, pierce_time_sec=2.0)

    result = compute_cutting_time([piece], material, quantity=1)

    quote = result.pieces[0]
    expected_unit_time = (48.0 / 20.0) + (2 * 2.0 / 60.0)
    assert quote.unit_time_min == pytest.approx(expected_unit_time)
