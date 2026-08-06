"""Generates a test DXF: a 10x6 inch rectangular plate with a 1-inch
diameter hole centered in it, in inch units.

Expected values for validating the engine's output against this file:
  - Outer perimeter: 32 in (2 * (10 + 6))
  - Hole circumference: ~3.14 in (pi * 1)
  - Total expected cut length: ~35.14 in
  - Bounding box: 10 x 6 in
  - Pierce count: 2 (outer contour + hole)
"""
import ezdxf

OUTPUT_PATH = "test_plate.dxf"


def make_test_plate(path: str = OUTPUT_PATH) -> None:
    doc = ezdxf.new(setup=True)
    doc.units = ezdxf.units.IN
    msp = doc.modelspace()

    msp.add_lwpolyline(
        [(0, 0), (10, 0), (10, 6), (0, 6)],
        close=True,
    )
    msp.add_circle(center=(5, 3), radius=0.5)

    doc.saveas(path)


if __name__ == "__main__":
    make_test_plate()
    print(f"Test DXF written to {OUTPUT_PATH}")
