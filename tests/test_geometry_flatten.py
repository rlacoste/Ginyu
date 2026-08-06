import math

import ezdxf
import pytest

from waterjet_quoter.geometry import flatten_entity, is_entity_closed


def _msp():
    return ezdxf.new().modelspace()


def test_flatten_line_returns_endpoints():
    msp = _msp()
    line = msp.add_line((0, 0), (3, 4))

    points = flatten_entity(line, distance=0.01)

    assert points[0] == pytest.approx((0, 0))
    assert points[-1] == pytest.approx((3, 4))


def test_flatten_circle_approximates_circumference():
    msp = _msp()
    circle = msp.add_circle(center=(0, 0), radius=1.0)

    points = flatten_entity(circle, distance=0.01)
    length = sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )

    assert length == pytest.approx(2 * math.pi, abs=0.01)


def test_is_entity_closed_circle_is_true():
    msp = _msp()
    circle = msp.add_circle(center=(0, 0), radius=1.0)
    assert is_entity_closed(circle) is True


def test_is_entity_closed_line_is_false():
    msp = _msp()
    line = msp.add_line((0, 0), (1, 1))
    assert is_entity_closed(line) is False


def test_is_entity_closed_lwpolyline_respects_close_flag():
    msp = _msp()
    closed_poly = msp.add_lwpolyline([(0, 0), (1, 0), (1, 1)], close=True)
    open_poly = msp.add_lwpolyline([(0, 0), (1, 0), (1, 1)], close=False)
    assert is_entity_closed(closed_poly) is True
    assert is_entity_closed(open_poly) is False


def test_is_entity_closed_spline_respects_closed_flag():
    msp = _msp()
    closed_spline = msp.add_spline(fit_points=[(0, 0), (5, 0), (5, 5), (0, 5)])
    closed_spline.closed = True
    open_spline = msp.add_spline(fit_points=[(0, 0), (5, 0), (5, 5), (0, 5)])
    assert is_entity_closed(closed_spline) is True
    assert is_entity_closed(open_spline) is False
