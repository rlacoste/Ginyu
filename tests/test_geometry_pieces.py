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
    # One warning for the incomplete contour itself, plus one for the fact
    # that this leaves zero extractable pieces overall.
    assert len(result.warnings) == 2
    assert any("incomplet" in w.lower() for w in result.warnings)
    assert any("Aucune pièce" in w for w in result.warnings)


def test_extract_pieces_includes_closed_spline_as_a_contour():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    spline = msp.add_spline(fit_points=[(0, 0), (10, 0), (10, 10), (0, 10)])
    spline.closed = True

    result = extract_pieces(doc)

    assert len(result.pieces) == 1
    piece = result.pieces[0]
    assert piece.pierce_count == 1
    assert piece.cut_length_in > 0
    # No warning: the spline should be chained into a piece, not dropped as
    # an incomplete contour.
    assert result.warnings == []


def test_extract_pieces_skips_zero_radius_circle_with_warning():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_circle(center=(0, 0), radius=0)

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("ignor" in w.lower() for w in result.warnings)


def test_extract_pieces_skips_unsupported_polymesh_with_warning():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    mesh = msp.add_polymesh(size=(3, 3))
    for i in range(3):
        for j in range(3):
            mesh.set_mesh_vertex((i, j), (i, j, 0))

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("ignor" in w.lower() for w in result.warnings)


def test_extract_pieces_empty_dxf_produces_no_pieces_warning():
    doc = ezdxf.new(setup=True)

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("Aucune pièce" in w for w in result.warnings)


def test_extract_pieces_skips_degenerate_spline_with_coincident_points():
    """Regression: a closed spline whose fit points are all coincident makes
    ezdxf.path.make_path() raise a bare IndexError (from ezdxf's internal
    knots_from_parametrization), not TypeError/ValueError. extract_pieces
    must catch this too, skip the entity, and warn instead of crashing.
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    spline = msp.add_spline(fit_points=[(0, 0), (0, 0), (0, 0), (0, 0)])
    spline.closed = True

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("ignor" in w.lower() for w in result.warnings)


def test_extract_pieces_skips_zero_length_line_alone_with_warning():
    """Regression: a zero-length LINE flattens to two identical points,
    passes the len(points) >= 2 guard, and gets chained into a fake
    "closed" contour with zero cut length -- silently inflating piece
    count/pierce time/price with no signal that anything was ignored.
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_line((20, 20), (20, 20))

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("ignor" in w.lower() or "nulle" in w.lower() for w in result.warnings)


def test_extract_pieces_skips_zero_length_line_alongside_real_piece():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 6), (0, 6)], close=True)
    msp.add_line((20, 20), (20, 20))

    result = extract_pieces(doc)

    assert len(result.pieces) == 1
    assert result.pieces[0].cut_length_in == pytest.approx(32.0, abs=1e-6)
    assert any("ignor" in w.lower() or "nulle" in w.lower() for w in result.warnings)


def test_extract_pieces_skips_zero_length_closed_polyline_with_warning():
    """A degenerate closed LWPOLYLINE (all vertices coincident) takes the
    "already closed" branch in extract_pieces (not the open-segment chainer)
    -- the length check must also apply there, not just post-chaining.
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_lwpolyline([(3, 3), (3, 3), (3, 3)], close=True)

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("ignor" in w.lower() or "nulle" in w.lower() for w in result.warnings)


def test_extract_pieces_filters_line_shorter_than_chaining_tolerance():
    """Regression: a LINE whose length falls below the chaining tolerance
    (default 1e-3 in) still snap-closes into a phantom 1-contour "piece" via
    _snap()'s rounding, even though it's nowhere near zero-length. A fixed
    _MIN_CONTOUR_LENGTH_IN of 1e-6 never caught this -- the degeneracy
    threshold must track chaining_tolerance itself, since any contour that
    only "closes" because two points snapped together within that tolerance
    is degenerate by construction.
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    # 2e-4 in: below the default 1e-3 chaining tolerance, but well above the
    # old fixed 1e-6 threshold -- exactly the gap the reviewer identified.
    msp.add_line((0, 0), (2e-4, 0))

    result = extract_pieces(doc)

    assert result.pieces == []
    assert any("ignor" in w.lower() or "nulle" in w.lower() for w in result.warnings)


def test_extract_pieces_filters_gap_length_line_alongside_real_piece():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 6), (0, 6)], close=True)
    msp.add_line((20, 20), (20 + 2e-4, 20))

    result = extract_pieces(doc)

    assert len(result.pieces) == 1
    assert result.pieces[0].cut_length_in == pytest.approx(32.0, abs=1e-6)
    assert any("ignor" in w.lower() or "nulle" in w.lower() for w in result.warnings)


def test_extract_pieces_does_not_filter_small_but_above_tolerance_contour():
    """Guard against over-filtering: a small but legitimate closed contour
    whose perimeter is comfortably above the chaining tolerance must still
    be treated as real geometry, not swept up by the degeneracy filter.
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    # Side length 0.01in -> perimeter 0.04in, ~40x the default 1e-3
    # chaining tolerance and still ~3x below a typical waterjet kerf, but
    # unambiguously not a snapping artefact.
    msp.add_lwpolyline(
        [(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01)], close=True
    )

    result = extract_pieces(doc)

    assert len(result.pieces) == 1
    assert result.pieces[0].cut_length_in == pytest.approx(0.04, abs=1e-6)
    assert not any("nulle" in w.lower() for w in result.warnings)


def test_extract_pieces_aggregates_incomplete_contour_warnings():
    """Regression: a DXF with many unrelated dangling LINE/ARC entities
    (typical of dimension/annotation lines mixed into the cut geometry)
    used to produce one "Contour incomplet..." warning per fragment. With
    dozens of such fragments the warning list becomes unreadable noise.
    They must be collapsed into a single summary warning instead.
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    # Three unrelated, non-touching open fragments, far apart so they can't
    # snap-chain into each other: a lone 2-point line, a 2-segment open
    # chain (3 points), and a 3-segment open chain (4 points).
    msp.add_line((0, 0), (1, 0))
    msp.add_line((100, 100), (101, 100))
    msp.add_line((101, 100), (101, 101))
    msp.add_line((200, 200), (201, 200))
    msp.add_line((201, 200), (201, 201))
    msp.add_line((201, 201), (202, 201))

    result = extract_pieces(doc)

    assert result.pieces == []
    incomplete_warnings = [w for w in result.warnings if "incomplet" in w.lower()]
    assert len(incomplete_warnings) == 1, (
        "expected exactly one aggregated warning, not one per fragment: "
        f"{result.warnings}"
    )
    assert "3" in incomplete_warnings[0]


def test_extract_pieces_flags_duplicate_pieces():
    """A client DXF that (accidentally) contains the same part traced twice
    -- e.g. once for real, once inside the title block -- must not pass
    through silently: no existing warning category catches "two distinct,
    individually valid pieces with near-identical geometry".
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 6), (0, 6)], close=True)
    msp.add_lwpolyline([(50, 50), (60, 50), (60, 56), (50, 56)], close=True)

    result = extract_pieces(doc)

    assert len(result.pieces) == 2
    duplicate_warnings = [w for w in result.warnings if "doublon" in w.lower()]
    assert len(duplicate_warnings) == 1
    assert "0" in duplicate_warnings[0] and "1" in duplicate_warnings[0]


def test_extract_pieces_does_not_flag_distinct_pieces_as_duplicates():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 6), (0, 6)], close=True)
    msp.add_lwpolyline([(50, 50), (58, 50), (58, 54), (50, 54)], close=True)

    result = extract_pieces(doc)

    assert len(result.pieces) == 2
    assert not any("doublon" in w.lower() for w in result.warnings)


def test_group_contours_unattachable_hole_treated_as_independent_piece():
    """Regression: when depth inflation makes find_parent return None,
    the odd-depth contour should become an independent piece, not crash.

    Scenario: L and K are unrelated boxes that overlap J's test point,
    inflating J's depth past I's, causing find_parent(I) to fail and return None.
    """
    def box(min_x, min_y, max_x, max_y):
        """Helper: create a closed rectangular contour."""
        return Contour(
            points=[
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
                (min_x, min_y),
            ]
        )

    # L and K are unrelated boxes that include the origin
    L = box(-10, -10, 5, 5)
    K = box(-20, -20, 10, 10)
    # J is the "true" outer piece; its first vertex (0, 0) falls inside L and K
    J = box(0, 0, 100, 100)
    # I is genuinely nested inside J only
    I = box(40, 40, 60, 60)

    # This should not crash with KeyError: None
    pieces = group_contours_into_pieces([L, K, J, I])

    # Verify I is represented and treated as its own piece (since parent could not be determined)
    all_contours_in_pieces = [c for p in pieces for c in p.contours]
    assert I in all_contours_in_pieces, "I should appear in some piece"
    # I should be the sole contour of its own piece due to orphaned parent
    assert any(p.contours == [I] for p in pieces), "I should be its own independent piece"


def test_group_contours_orphaned_parent_not_in_dict():
    """Regression: when find_parent returns an index of an odd-depth contour
    that was already attached as a child (not a dict key in pieces_by_outer_index),
    the child should not crash but become an independent piece.

    The 5-box configuration that reproduces this:
    - boxes: [(10,6)-(11,32), (-5,10)-(19,34), (2,-10)-(32,-8), (10,13)-(32,43), (-10,4)-(13,14)]
    - depths: [1, 1, 0, 3, 0]
    - contour 3 finds parent_idx=0, but 0 was already attached to 4 as a child,
      so pieces_by_outer_index[0] doesn't exist.
    """
    def box(min_x, min_y, max_x, max_y):
        """Helper: create a closed rectangular contour."""
        return Contour(
            points=[
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
                (min_x, min_y),
            ]
        )

    # Exact 5-box configuration from the reviewer
    box0 = box(10, 6, 11, 32)     # depth 1
    box1 = box(-5, 10, 19, 34)    # depth 1
    box2 = box(2, -10, 32, -8)    # depth 0
    box3 = box(10, 13, 32, 43)    # depth 3
    box4 = box(-10, 4, 13, 14)    # depth 0

    # This should not crash with KeyError (whether None or missing key)
    pieces = group_contours_into_pieces([box0, box1, box2, box3, box4])

    # Verify all contours are represented somewhere
    all_contours_in_pieces = [c for p in pieces for c in p.contours]
    assert box0 in all_contours_in_pieces
    assert box1 in all_contours_in_pieces
    assert box2 in all_contours_in_pieces
    assert box3 in all_contours_in_pieces
    assert box4 in all_contours_in_pieces
    assert len(all_contours_in_pieces) == 5, "All 5 contours should be preserved"
