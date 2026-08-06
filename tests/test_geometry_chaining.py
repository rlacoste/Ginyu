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


def test_connected_open_path_chains_bidirectionally():
    """Regression test: a single connected open path with middle segment listed first.

    Segments form: (0,0)--(4,0)--(2,3)--(5,5)
    When middle segment [(4,0),(2,3)] is processed first, the algorithm must
    extend BOTH directions to capture the full path as one incomplete contour.
    """
    segments = [
        [(4, 0), (2, 3)],
        [(2, 3), (5, 5)],
        [(0, 0), (4, 0)],
    ]

    result = chain_open_segments(segments, tolerance=1e-3)

    # Should be ONE incomplete contour, not multiple fragments
    assert len(result.closed_contours) == 0
    assert len(result.incomplete_contours) == 1

    # Verify all points are in the chain and path is connected
    chain = result.incomplete_contours[0]
    points_set = set(chain)
    assert (0, 0) in points_set
    assert (4, 0) in points_set
    assert (2, 3) in points_set
    assert (5, 5) in points_set

    # Verify the perimeter is correct: |0-4| + |4-2,3| + |2,3-5,5|
    length = sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(chain, chain[1:])
    )
    expected = 4 + math.hypot(2, 3) + math.hypot(3, 2)
    assert length == pytest.approx(expected, abs=1e-6)
