import ezdxf

from waterjet_quoter.make_test_dxf import make_test_plate


def test_make_test_plate_creates_expected_entities(tmp_path):
    dxf_path = tmp_path / "plate.dxf"

    make_test_plate(str(dxf_path))

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    entities = list(msp)
    dxftypes = sorted(e.dxftype() for e in entities)

    assert dxftypes == ["CIRCLE", "LWPOLYLINE"]

    polyline = next(e for e in entities if e.dxftype() == "LWPOLYLINE")
    assert polyline.is_closed
    points = [(p[0], p[1]) for p in polyline.get_points()]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    assert max(xs) - min(xs) == 10
    assert max(ys) - min(ys) == 6

    circle = next(e for e in entities if e.dxftype() == "CIRCLE")
    assert circle.dxf.radius == 0.5
    assert circle.dxf.center == (5, 3, 0)
