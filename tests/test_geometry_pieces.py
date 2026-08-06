import ezdxf
import pytest

from waterjet_quoter.geometry import (
    Contour,
    point_in_polygon,
    polyline_length,
    group_contours_into_pieces,
    extract_pieces,
)


def test_polyline_length_sums_segments():
    points = [(0, 0), (3, 0), (3, 4)]
    assert polyline_length(points) == pytest.approx(7.0)


def test_point_in_polygon_true_for_inside_point():
    square = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    assert point_in_polygon((5, 5), square) is True


def test_point_in_polygon_false_for_outside_point():
    square = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    assert point_in_polygon((15, 5), square) is False


def test_group_contours_attaches_hole_to_outer_piece():
    outer = Contour(points=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    hole = Contour(points=[(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)])

    pieces = group_contours_into_pieces([outer, hole])

    assert len(pieces) == 1
    piece = pieces[0]
    assert piece.pierce_count == 2
    assert piece.cut_length_in == pytest.approx(40.0 + 8.0)
    assert piece.bbox == pytest.approx((10.0, 10.0))
    assert piece.area_in2 == pytest.approx(100.0)


def test_group_contours_two_separate_outer_pieces():
    piece_a = Contour(points=[(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
    piece_b = Contour(points=[(20, 0), (22, 0), (22, 2), (20, 2), (20, 0)])

    pieces = group_contours_into_pieces([piece_a, piece_b])

    assert len(pieces) == 2
    assert all(p.pierce_count == 1 for p in pieces)


def test_extract_pieces_from_rectangle_with_hole():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 6), (0, 6)], close=True)
    msp.add_circle(center=(5, 3), radius=0.5)

    result = extract_pieces(doc)

    assert len(result.pieces) == 1
    piece = result.pieces[0]
    assert piece.pierce_count == 2
    assert piece.cut_length_in == pytest.approx(35.14, abs=0.05)
    assert piece.bbox == pytest.approx((10.0, 6.0), abs=1e-6)
    assert piece.area_in2 == pytest.approx(60.0, abs=1e-6)
    assert result.warnings == []


def test_extract_pieces_chains_loose_line_arc_segments():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_line((0, 0), (4, 0))
    msp.add_line((4, 0), (2, 3))
    msp.add_line((2, 3), (0, 0))

    result = extract_pieces(doc)

    assert len(result.pieces) == 1
    assert result.pieces[0].pierce_count == 1
    assert result.warnings == []


def test_extract_pieces_reports_incomplete_contour_as_warning():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_line((0, 0), (4, 0))
    msp.add_line((4, 0), (2, 3))

    result = extract_pieces(doc)

    assert len(result.pieces) == 0
    assert len(result.warnings) == 1
