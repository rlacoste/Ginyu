import math

import pytest

from waterjet_quoter.geometry import chain_open_segments


def test_chains_three_segments_into_closed_triangle():
    segments = [
        [(0, 0), (4, 0)],
        [(4, 0), (2, 3)],
        [(2, 3), (0, 0)],
    ]

    result = chain_open_segments(segments, tolerance=1e-3)

    assert len(result.closed_contours) == 1
    assert len(result.incomplete_contours) == 0
    contour = result.closed_contours[0]
    length = sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(contour, contour[1:])
    )
    expected = 4 + math.hypot(2, 3) + math.hypot(2, 3)
    assert length == pytest.approx(expected, abs=1e-6)


def test_chains_segments_regardless_of_order_and_direction():
    segments = [
        [(2, 3), (0, 0)],
        [(0, 0), (4, 0)],
        [(2, 3), (4, 0)],
    ]

    result = chain_open_segments(segments, tolerance=1e-3)

    assert len(result.closed_contours) == 1
    assert len(result.incomplete_contours) == 0


def test_leftover_segments_reported_as_incomplete():
    segments = [
        [(0, 0), (4, 0)],
        [(4, 0), (2, 3)],
    ]

    result = chain_open_segments(segments, tolerance=1e-3)

    assert len(result.closed_contours) == 0
    assert len(result.incomplete_contours) == 1
