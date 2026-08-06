# Waterjet Quoting Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that reads a DXF file, extracts per-piece cut geometry, and produces a rough waterjet cutting quote (cutting time, material sheets needed, price breakdown) as both human-readable text and a structured dict/JSON.

**Architecture:** A small package (`waterjet_quoter/`) with one module per responsibility — file ingestion (replaceable boundary), geometry extraction (ezdxf-only, no shapely), a JSON-backed materials table, cost calculation, and output formatting — wired together by a thin CLI entry point. See `docs/superpowers/specs/2026-08-06-waterjet-quoting-engine-design.md` for the full design rationale.

**Tech Stack:** Python 3.9+, `ezdxf` (DXF parsing), `pytest` (tests). No other third-party dependencies.

## Global Constraints

- Only third-party dependencies: `ezdxf` (runtime) and `pytest` (tests). No `shapely` or other geometry library.
- Materials table lives in `waterjet_quoter/materials.json`, loaded at runtime — never hard-coded in calculation logic.
- A missing (material, thickness, quality) triplet raises `MaterialNotFoundError` — never a guessed default.
- CLI only, no database, no web interface: `python -m waterjet_quoter.main <dxf_path> --material <str> --thickness <str> [--quality standard] [--qty 1]`.
- Every quote run produces both a human-readable report and a structured dict/JSON via the same `run()` call — other components will consume the structured form later.
- Adjustable business constants (nesting utilization factor default `0.75`, machine rate default `125`/hour, sheet cost per material, flat labor fees, large-piece warning threshold `40` in, standard sheet `48x96` in) all live in `config.py`, nowhere else.
- Geometry extraction handles LINE, ARC, CIRCLE, LWPOLYLINE, POLYLINE, SPLINE via `ezdxf.path` flattening (one mechanism for all types), with tolerance-based chaining of open segments and depth-based point-in-polygon containment for grouping contours into pieces (outer boundary vs. hole vs. nested island).
- `--qty` from the CLI is the quantity; the engine does not attempt duplicate-piece detection.

---

## Task 1: Project scaffolding + config.py

**Files:**
- Create: `waterjet_quoter/__init__.py`
- Create: `waterjet_quoter/config.py`
- Create: `requirements.txt`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: module `waterjet_quoter.config` with constants `NESTING_UTILIZATION_FACTOR: float`, `SHEET_WIDTH_IN: float`, `SHEET_HEIGHT_IN: float`, `LARGE_PIECE_DIMENSION_THRESHOLD_IN: float`, `MACHINE_RATE_PER_HOUR: float`, `SHEET_COST_BY_MATERIAL: dict[str, float]`, `LABOR_FLAT_FEES: dict[str, float]`, `CHAINING_TOLERANCE_IN: float`, `FLATTENING_DISTANCE_IN: float`

- [ ] **Step 1: Create the package and repo scaffolding**

```bash
mkdir -p waterjet_quoter tests
touch waterjet_quoter/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
ezdxf>=1.3
pytest>=8.0
```

- [ ] **Step 3: Set up a virtualenv and install dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Write the failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 5: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.config'`

- [ ] **Step 6: Write config.py**

```python
# waterjet_quoter/config.py
"""Adjustable business constants for the waterjet quoting engine.

Change values here; nothing in geometry.py, materials.py, or costing.py
should hard-code any of these.
"""

# Fraction of a standard sheet assumed usable after nesting losses.
NESTING_UTILIZATION_FACTOR = 0.75

# Standard sheet size, in inches.
SHEET_WIDTH_IN = 48.0
SHEET_HEIGHT_IN = 96.0

# If a piece's largest bounding-box dimension exceeds this, flag a warning
# that the area-based material estimate is unreliable for it.
LARGE_PIECE_DIMENSION_THRESHOLD_IN = 40.0

# Machine time cost, in dollars per hour.
MACHINE_RATE_PER_HOUR = 125.0

# Sheet cost per material, in dollars. Placeholder values -- replace with
# real supplier pricing.
SHEET_COST_BY_MATERIAL = {
    "aluminum": 220.0,
    "mild_steel": 150.0,
    "stainless_steel": 340.0,
}

# Flat labor fees applied per job, in dollars. Placeholder values.
LABOR_FLAT_FEES = {
    "programming": 45.0,
    "setup": 35.0,
    "shipping": 25.0,
}

# Tolerance (inches) used to decide whether two contour endpoints are the
# same point when chaining loose LINE/ARC segments into closed loops.
CHAINING_TOLERANCE_IN = 1e-3

# Maximum deviation (inches) allowed when flattening curves (ARC, CIRCLE,
# SPLINE) into straight-line segments for length/perimeter calculations.
FLATTENING_DISTANCE_IN = 0.01
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (7 tests)

- [ ] **Step 8: Commit**

```bash
git add waterjet_quoter/__init__.py waterjet_quoter/config.py requirements.txt tests/test_config.py
git commit -m "Add project scaffolding and adjustable business config"
```

---

## Task 2: materials.py + materials.json

**Files:**
- Create: `waterjet_quoter/materials.json`
- Create: `waterjet_quoter/materials.py`
- Test: `tests/test_materials.py`

**Interfaces:**
- Consumes: nothing
- Produces: `waterjet_quoter.materials.MaterialParams` (frozen dataclass: `feed_rate_ipm: float`, `pierce_time_sec: float`), `MaterialNotFoundError` (exception), `DEFAULT_TABLE_PATH: Path`, `load_table(path: Path = DEFAULT_TABLE_PATH) -> dict`, `lookup(material: str, thickness: str, quality: str = "standard", table: Optional[dict] = None) -> MaterialParams`

- [ ] **Step 1: Write materials.json**

```json
{
  "aluminum": {
    "6mm": { "standard": { "feed_rate_ipm": 18.0, "pierce_time_sec": 3.0 } },
    "12mm": { "standard": { "feed_rate_ipm": 9.0, "pierce_time_sec": 6.0 } }
  },
  "mild_steel": {
    "6mm": { "standard": { "feed_rate_ipm": 14.0, "pierce_time_sec": 4.0 } },
    "12mm": { "standard": { "feed_rate_ipm": 7.0, "pierce_time_sec": 8.0 } }
  },
  "stainless_steel": {
    "6mm": { "standard": { "feed_rate_ipm": 10.0, "pierce_time_sec": 5.0 } },
    "12mm": { "standard": { "feed_rate_ipm": 5.0, "pierce_time_sec": 10.0 } }
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_materials.py
import pytest

from waterjet_quoter.materials import (
    MaterialNotFoundError,
    lookup,
    load_table,
)

REQUIRED_COMBOS = [
    ("aluminum", "6mm"),
    ("aluminum", "12mm"),
    ("mild_steel", "6mm"),
    ("mild_steel", "12mm"),
    ("stainless_steel", "6mm"),
    ("stainless_steel", "12mm"),
]


def test_shipped_table_has_all_required_combos():
    table = load_table()
    for material, thickness in REQUIRED_COMBOS:
        params = lookup(material, thickness, table=table)
        assert params.feed_rate_ipm > 0
        assert params.pierce_time_sec > 0


def test_lookup_default_quality_is_standard():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    params = lookup("aluminum", "6mm", table=table)
    assert params.feed_rate_ipm == 18.0
    assert params.pierce_time_sec == 3.0


def test_lookup_raises_for_unknown_material():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    with pytest.raises(MaterialNotFoundError):
        lookup("titanium", "6mm", table=table)


def test_lookup_raises_for_unknown_thickness():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    with pytest.raises(MaterialNotFoundError):
        lookup("aluminum", "20mm", table=table)


def test_lookup_raises_for_unknown_quality():
    table = {"aluminum": {"6mm": {"standard": {"feed_rate_ipm": 18.0, "pierce_time_sec": 3.0}}}}
    with pytest.raises(MaterialNotFoundError):
        lookup("aluminum", "6mm", quality="fine", table=table)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_materials.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.materials'`

- [ ] **Step 4: Write materials.py**

```python
# waterjet_quoter/materials.py
"""Loads and looks up the materials reference table (feed rate, pierce time).

The table lives in materials.json, indexed by material -> thickness ->
quality. This module only knows how to read that file and look values up.
Migrating the table to a database later should only require changing
load_table(); costing.py never touches the table directly.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_TABLE_PATH = Path(__file__).parent / "materials.json"


class MaterialNotFoundError(KeyError):
    """Raised when a (material, thickness, quality) triplet is not in the table."""


@dataclass(frozen=True)
class MaterialParams:
    feed_rate_ipm: float
    pierce_time_sec: float


def load_table(path: Path = DEFAULT_TABLE_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def lookup(
    material: str,
    thickness: str,
    quality: str = "standard",
    table: Optional[dict] = None,
) -> MaterialParams:
    if table is None:
        table = load_table()
    try:
        entry = table[material][thickness][quality]
    except KeyError:
        raise MaterialNotFoundError(
            f"No cutting parameters found for material={material!r}, "
            f"thickness={thickness!r}, quality={quality!r}. "
            f"Check materials.json."
        ) from None
    return MaterialParams(
        feed_rate_ipm=entry["feed_rate_ipm"],
        pierce_time_sec=entry["pierce_time_sec"],
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_materials.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add waterjet_quoter/materials.json waterjet_quoter/materials.py tests/test_materials.py
git commit -m "Add materials reference table and lookup"
```

---

## Task 3: ingestion.py (file source boundary)

**Files:**
- Create: `waterjet_quoter/ingestion.py`
- Test: `tests/test_ingestion.py`

**Interfaces:**
- Consumes: nothing
- Produces: `waterjet_quoter.ingestion.load_dxf(source: str) -> ezdxf.document.Drawing`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingestion.py
import ezdxf
import pytest

from waterjet_quoter.ingestion import load_dxf


def test_load_dxf_returns_drawing_with_expected_entity(tmp_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (1, 1))
    dxf_path = tmp_path / "sample.dxf"
    doc.saveas(dxf_path)

    drawing = load_dxf(str(dxf_path))

    entities = list(drawing.modelspace())
    assert len(entities) == 1
    assert entities[0].dxftype() == "LINE"


def test_load_dxf_raises_for_missing_file():
    with pytest.raises(FileNotFoundError):
        load_dxf("/nonexistent/path/does_not_exist.dxf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingestion.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.ingestion'`

- [ ] **Step 3: Write ingestion.py**

```python
# waterjet_quoter/ingestion.py
"""File source boundary.

Today the DXF comes from a local file path. Later this will be replaced by
a connection to an upstream pipeline (e.g. iGEMS). Nothing downstream of
load_dxf() should know or care where the file came from -- it only ever
sees an already-loaded ezdxf.Drawing.
"""
import ezdxf
from ezdxf.document import Drawing


def load_dxf(source: str) -> Drawing:
    """Load a DXF file from a local path and return its ezdxf Drawing.

    Raises FileNotFoundError if the path does not exist, and
    ezdxf.DXFStructureError if the file is not a valid DXF.
    """
    return ezdxf.readfile(source)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingestion.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/ingestion.py tests/test_ingestion.py
git commit -m "Add DXF ingestion boundary"
```

---

## Task 4: make_test_dxf.py (test fixture generator)

**Files:**
- Create: `waterjet_quoter/make_test_dxf.py`
- Test: `tests/test_make_test_dxf.py`

**Interfaces:**
- Consumes: nothing
- Produces: `waterjet_quoter.make_test_dxf.make_test_plate(path: str = OUTPUT_PATH) -> None`, `OUTPUT_PATH: str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_make_test_dxf.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_make_test_dxf.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.make_test_dxf'`

- [ ] **Step 3: Write make_test_dxf.py**

```python
# waterjet_quoter/make_test_dxf.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_make_test_dxf.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/make_test_dxf.py tests/test_make_test_dxf.py
git commit -m "Add test DXF fixture generator"
```

---

## Task 5: geometry.py — entity flattening and closed-entity detection

**Files:**
- Create: `waterjet_quoter/geometry.py`
- Test: `tests/test_geometry_flatten.py`

**Interfaces:**
- Consumes: nothing
- Produces: `waterjet_quoter.geometry.Point` (type alias `Tuple[float, float]`), `SUPPORTED_DXFTYPES: set`, `flatten_entity(entity, distance: float) -> List[Point]`, `is_entity_closed(entity) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_geometry_flatten.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_geometry_flatten.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.geometry'`

- [ ] **Step 3: Write geometry.py (flattening section)**

```python
# waterjet_quoter/geometry.py
"""Geometric extraction: turns DXF entities into per-piece cut geometry.

Handles LINE, ARC, CIRCLE, LWPOLYLINE, POLYLINE, and SPLINE entities via
ezdxf's path-flattening, so every entity type is reduced to the same
representation (a polyline of points) before any geometry math happens.
"""
import math
from dataclasses import dataclass
from typing import List, Tuple

import ezdxf.path
from ezdxf.document import Drawing

from . import config

Point = Tuple[float, float]

SUPPORTED_DXFTYPES = {"LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE", "SPLINE"}


def flatten_entity(entity, distance: float) -> List[Point]:
    """Convert any supported DXF entity into a polyline of (x, y) points."""
    path = ezdxf.path.make_path(entity)
    return [(v.x, v.y) for v in path.flattening(distance)]


def is_entity_closed(entity) -> bool:
    """True if the entity is inherently a closed loop on its own."""
    dxftype = entity.dxftype()
    if dxftype == "CIRCLE":
        return True
    if dxftype in ("LWPOLYLINE", "POLYLINE"):
        return bool(entity.is_closed)
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_geometry_flatten.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/geometry.py tests/test_geometry_flatten.py
git commit -m "Add DXF entity flattening and closed-entity detection"
```

---

## Task 6: geometry.py — chaining open segments into closed loops

**Files:**
- Modify: `waterjet_quoter/geometry.py`
- Test: `tests/test_geometry_chaining.py`

**Interfaces:**
- Consumes: `Point` from Task 5
- Produces: `ChainResult` (dataclass: `closed_contours: List[List[Point]]`, `incomplete_contours: List[List[Point]]`), `chain_open_segments(segments: List[List[Point]], tolerance: float) -> ChainResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_geometry_chaining.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_geometry_chaining.py -v`
Expected: FAIL with `ImportError: cannot import name 'chain_open_segments'`

- [ ] **Step 3: Add chaining to geometry.py**

Append to `waterjet_quoter/geometry.py`:

```python
def _snap(point: Point, tolerance: float) -> Point:
    ndigits = max(0, -int(math.floor(math.log10(tolerance))))
    return (round(point[0], ndigits), round(point[1], ndigits))


@dataclass
class ChainResult:
    closed_contours: List[List[Point]]
    incomplete_contours: List[List[Point]]


def chain_open_segments(segments: List[List[Point]], tolerance: float) -> ChainResult:
    """Chain open polylines end-to-end into closed loops.

    Each item in `segments` is a flattened polyline for one open DXF
    entity (its first and last points are the entity's endpoints). Returns
    the polylines that could be chained into closed loops, and any leftover
    open chains that never closed (reported as incomplete). Assumes simple
    loops -- exactly two segments meet at each junction point.
    """
    remaining = list(range(len(segments)))
    closed_contours: List[List[Point]] = []
    incomplete_contours: List[List[Point]] = []

    while remaining:
        start_idx = remaining.pop(0)
        chain = list(segments[start_idx])
        start_key = _snap(chain[0], tolerance)

        progressed = True
        while progressed:
            progressed = False
            current_key = _snap(chain[-1], tolerance)
            if current_key == start_key and len(chain) > 1:
                break
            for i, idx in enumerate(remaining):
                seg = segments[idx]
                if _snap(seg[0], tolerance) == current_key:
                    chain.extend(seg[1:])
                    remaining.pop(i)
                    progressed = True
                    break
                if _snap(seg[-1], tolerance) == current_key:
                    chain.extend(list(reversed(seg))[1:])
                    remaining.pop(i)
                    progressed = True
                    break

        if _snap(chain[-1], tolerance) == start_key and len(chain) > 1:
            closed_contours.append(chain)
        else:
            incomplete_contours.append(chain)

    return ChainResult(closed_contours, incomplete_contours)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_geometry_chaining.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/geometry.py tests/test_geometry_chaining.py
git commit -m "Add tolerance-based chaining of open contour segments"
```

---

## Task 7: geometry.py — containment grouping and extract_pieces

**Files:**
- Modify: `waterjet_quoter/geometry.py`
- Test: `tests/test_geometry_pieces.py`

**Interfaces:**
- Consumes: `flatten_entity`, `is_entity_closed`, `SUPPORTED_DXFTYPES` from Task 5; `chain_open_segments`, `ChainResult` from Task 6; `config.FLATTENING_DISTANCE_IN`, `config.CHAINING_TOLERANCE_IN` from Task 1
- Produces: `polyline_length(points: List[Point]) -> float`, `point_in_polygon(point: Point, polygon: List[Point]) -> bool`, `Contour` (dataclass: `points: List[Point]`), `Piece` (dataclass: `piece_id: int`, `contours: List[Contour]`, properties `cut_length_in`, `pierce_count`, `bbox`, `area_in2`), `group_contours_into_pieces(contours: List[Contour]) -> List[Piece]`, `ExtractionResult` (dataclass: `pieces: List[Piece]`, `warnings: List[str]`), `extract_pieces(drawing: Drawing, flattening_distance: float = config.FLATTENING_DISTANCE_IN, chaining_tolerance: float = config.CHAINING_TOLERANCE_IN) -> ExtractionResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_geometry_pieces.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_geometry_pieces.py -v`
Expected: FAIL with `ImportError: cannot import name 'point_in_polygon'`

- [ ] **Step 3: Add containment grouping and extract_pieces to geometry.py**

Append to `waterjet_quoter/geometry.py`:

```python
def polyline_length(points: List[Point]) -> float:
    return sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )


def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
    """Ray-casting point-in-polygon test. `polygon` is a closed loop of points."""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_intersect:
                inside = not inside
    return inside


@dataclass
class Contour:
    points: List[Point]


@dataclass
class Piece:
    piece_id: int
    contours: List[Contour]

    @property
    def cut_length_in(self) -> float:
        return sum(polyline_length(c.points) for c in self.contours)

    @property
    def pierce_count(self) -> int:
        return len(self.contours)

    @property
    def bbox(self) -> Tuple[float, float]:
        xs = [p[0] for c in self.contours for p in c.points]
        ys = [p[1] for c in self.contours for p in c.points]
        return (max(xs) - min(xs), max(ys) - min(ys))

    @property
    def area_in2(self) -> float:
        width, height = self.bbox
        return width * height


def _contour_depth(index: int, contours: List[Contour]) -> int:
    test_point = contours[index].points[0]
    depth = 0
    for j, other in enumerate(contours):
        if j == index:
            continue
        if point_in_polygon(test_point, other.points):
            depth += 1
    return depth


def group_contours_into_pieces(contours: List[Contour]) -> List[Piece]:
    """Group contours into pieces using nesting-depth parity.

    A contour's depth is how many other contours contain it. Even depth
    (0, 2, 4...) starts a new piece (an outer boundary, or a solid island
    sitting inside a hole). Odd depth is a hole, attached to its direct
    parent (the next contour up in depth that contains it).
    """
    depths = [_contour_depth(i, contours) for i in range(len(contours))]

    def find_parent(i: int) -> int:
        best_parent = None
        best_depth = -1
        for j, other in enumerate(contours):
            if j == i or depths[j] >= depths[i]:
                continue
            if point_in_polygon(contours[i].points[0], other.points) and depths[j] > best_depth:
                best_parent = j
                best_depth = depths[j]
        return best_parent

    pieces_by_outer_index = {}
    pieces: List[Piece] = []
    next_id = 0

    for i in sorted(range(len(contours)), key=lambda idx: depths[idx]):
        if depths[i] % 2 == 0:
            piece = Piece(piece_id=next_id, contours=[contours[i]])
            pieces_by_outer_index[i] = piece
            pieces.append(piece)
            next_id += 1
        else:
            parent_idx = find_parent(i)
            pieces_by_outer_index[parent_idx].contours.append(contours[i])

    return pieces


@dataclass
class ExtractionResult:
    pieces: List[Piece]
    warnings: List[str]


def extract_pieces(
    drawing: Drawing,
    flattening_distance: float = config.FLATTENING_DISTANCE_IN,
    chaining_tolerance: float = config.CHAINING_TOLERANCE_IN,
) -> ExtractionResult:
    msp = drawing.modelspace()

    closed_contours: List[Contour] = []
    open_segments: List[List[Point]] = []

    for entity in msp:
        if entity.dxftype() not in SUPPORTED_DXFTYPES:
            continue
        points = flatten_entity(entity, flattening_distance)
        if is_entity_closed(entity):
            if points[0] != points[-1]:
                points = points + [points[0]]
            closed_contours.append(Contour(points=points))
        else:
            open_segments.append(points)

    warnings: List[str] = []
    if open_segments:
        chain_result = chain_open_segments(open_segments, chaining_tolerance)
        closed_contours.extend(Contour(points=c) for c in chain_result.closed_contours)
        for incomplete in chain_result.incomplete_contours:
            warnings.append(
                f"Contour incomplet détecté ({len(incomplete)} points) — "
                f"segments non refermés en boucle, exclu du calcul."
            )

    pieces = group_contours_into_pieces(closed_contours)
    return ExtractionResult(pieces=pieces, warnings=warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_geometry_pieces.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Run the full geometry test suite**

Run: `pytest tests/test_geometry_flatten.py tests/test_geometry_chaining.py tests/test_geometry_pieces.py -v`
Expected: PASS (16 tests)

- [ ] **Step 6: Commit**

```bash
git add waterjet_quoter/geometry.py tests/test_geometry_pieces.py
git commit -m "Add depth-based contour containment and extract_pieces"
```

---

## Task 8: costing.py — cutting time calculation

**Files:**
- Create: `waterjet_quoter/costing.py`
- Test: `tests/test_costing_time.py`

**Interfaces:**
- Consumes: `Piece` (`cut_length_in`, `pierce_count`, `bbox`, `piece_id`, `area_in2`) from Task 7; `MaterialParams` (`feed_rate_ipm`, `pierce_time_sec`) from Task 2
- Produces: `PieceQuote` (dataclass: `piece_id: int`, `cut_length_in: float`, `pierce_count: int`, `bbox_width_in: float`, `bbox_height_in: float`, `area_in2: float`, `unit_time_min: float`), `CuttingTimeResult` (dataclass: `pieces: List[PieceQuote]`, `total_time_min: float`), `compute_cutting_time(pieces: List[Piece], material: MaterialParams, quantity: int) -> CuttingTimeResult`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_costing_time.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.costing'`

- [ ] **Step 3: Write costing.py (cutting time section)**

```python
# waterjet_quoter/costing.py
"""Cutting time, material estimate, and price calculations."""
import math
from dataclasses import dataclass
from typing import List

from . import config
from .geometry import Piece
from .materials import MaterialParams


@dataclass
class PieceQuote:
    piece_id: int
    cut_length_in: float
    pierce_count: int
    bbox_width_in: float
    bbox_height_in: float
    area_in2: float
    unit_time_min: float


@dataclass
class CuttingTimeResult:
    pieces: List[PieceQuote]
    total_time_min: float


def compute_cutting_time(
    pieces: List[Piece], material: MaterialParams, quantity: int
) -> CuttingTimeResult:
    piece_quotes = []
    total_time_min = 0.0
    for piece in pieces:
        width, height = piece.bbox
        pierce_time_min = (piece.pierce_count * material.pierce_time_sec) / 60.0
        cut_time_min = piece.cut_length_in / material.feed_rate_ipm
        unit_time_min = cut_time_min + pierce_time_min
        total_time_min += unit_time_min * quantity
        piece_quotes.append(
            PieceQuote(
                piece_id=piece.piece_id,
                cut_length_in=piece.cut_length_in,
                pierce_count=piece.pierce_count,
                bbox_width_in=width,
                bbox_height_in=height,
                area_in2=piece.area_in2,
                unit_time_min=unit_time_min,
            )
        )
    return CuttingTimeResult(pieces=piece_quotes, total_time_min=total_time_min)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_costing_time.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/costing.py tests/test_costing_time.py
git commit -m "Add cutting time calculation"
```

---

## Task 9: costing.py — material estimate calculation

**Files:**
- Modify: `waterjet_quoter/costing.py`
- Test: `tests/test_costing_material.py`

**Interfaces:**
- Consumes: `Piece` (`bbox`, `area_in2`, `piece_id`) from Task 7; `config.SHEET_WIDTH_IN`, `config.SHEET_HEIGHT_IN`, `config.NESTING_UTILIZATION_FACTOR`, `config.LARGE_PIECE_DIMENSION_THRESHOLD_IN` from Task 1
- Produces: `MaterialEstimateResult` (dataclass: `total_area_in2: float`, `sheets_needed: int`, `utilization_factor: float`, `warnings: List[str]`), `estimate_material(pieces: List[Piece], quantity: int) -> MaterialEstimateResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_costing_material.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_costing_material.py -v`
Expected: FAIL with `ImportError: cannot import name 'estimate_material'`

- [ ] **Step 3: Add estimate_material to costing.py**

Append to `waterjet_quoter/costing.py`:

```python
@dataclass
class MaterialEstimateResult:
    total_area_in2: float
    sheets_needed: int
    utilization_factor: float
    warnings: List[str]


def estimate_material(pieces: List[Piece], quantity: int) -> MaterialEstimateResult:
    warnings = []
    total_area_in2 = 0.0
    for piece in pieces:
        width, height = piece.bbox
        total_area_in2 += piece.area_in2 * quantity
        if max(width, height) > config.LARGE_PIECE_DIMENSION_THRESHOLD_IN:
            warnings.append(
                f"Pièce {piece.piece_id}: dimension max "
                f"{max(width, height):.1f} po dépasse le seuil de "
                f"{config.LARGE_PIECE_DIMENSION_THRESHOLD_IN} po — nesting "
                f"manuel recommandé — estimation matière peu fiable pour "
                f"cette pièce."
            )

    sheet_area_in2 = config.SHEET_WIDTH_IN * config.SHEET_HEIGHT_IN
    usable_area_in2 = sheet_area_in2 * config.NESTING_UTILIZATION_FACTOR
    sheets_needed = (
        math.ceil(total_area_in2 / usable_area_in2) if total_area_in2 > 0 else 0
    )

    return MaterialEstimateResult(
        total_area_in2=total_area_in2,
        sheets_needed=sheets_needed,
        utilization_factor=config.NESTING_UTILIZATION_FACTOR,
        warnings=warnings,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_costing_material.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/costing.py tests/test_costing_material.py
git commit -m "Add material sheet estimate with large-piece warning"
```

---

## Task 10: costing.py — price calculation

**Files:**
- Modify: `waterjet_quoter/costing.py`
- Test: `tests/test_costing_price.py`

**Interfaces:**
- Consumes: `config.MACHINE_RATE_PER_HOUR`, `config.SHEET_COST_BY_MATERIAL`, `config.LABOR_FLAT_FEES` from Task 1
- Produces: `PricingResult` (dataclass: `machine_time_cost: float`, `material_cost: float`, `labor_cost: float`, `total_price: float`), `compute_price(total_time_min: float, sheets_needed: int, material: str) -> PricingResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_costing_price.py
import pytest

from waterjet_quoter.costing import compute_price
from waterjet_quoter import config


def test_compute_price_breaks_down_components():
    result = compute_price(total_time_min=120.0, sheets_needed=3, material="aluminum")

    expected_machine_cost = (120.0 / 60.0) * config.MACHINE_RATE_PER_HOUR
    expected_material_cost = 3 * config.SHEET_COST_BY_MATERIAL["aluminum"]
    expected_labor_cost = sum(config.LABOR_FLAT_FEES.values())

    assert result.machine_time_cost == pytest.approx(expected_machine_cost)
    assert result.material_cost == pytest.approx(expected_material_cost)
    assert result.labor_cost == pytest.approx(expected_labor_cost)
    assert result.total_price == pytest.approx(
        expected_machine_cost + expected_material_cost + expected_labor_cost
    )


def test_compute_price_raises_for_unknown_material():
    with pytest.raises(KeyError):
        compute_price(total_time_min=60.0, sheets_needed=1, material="titanium")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_costing_price.py -v`
Expected: FAIL with `ImportError: cannot import name 'compute_price'`

- [ ] **Step 3: Add compute_price to costing.py**

Append to `waterjet_quoter/costing.py`:

```python
@dataclass
class PricingResult:
    machine_time_cost: float
    material_cost: float
    labor_cost: float
    total_price: float


def compute_price(total_time_min: float, sheets_needed: int, material: str) -> PricingResult:
    if material not in config.SHEET_COST_BY_MATERIAL:
        raise KeyError(
            f"No sheet cost configured for material {material!r} in "
            f"config.SHEET_COST_BY_MATERIAL."
        )
    machine_time_cost = (total_time_min / 60.0) * config.MACHINE_RATE_PER_HOUR
    material_cost = sheets_needed * config.SHEET_COST_BY_MATERIAL[material]
    labor_cost = sum(config.LABOR_FLAT_FEES.values())
    total_price = machine_time_cost + material_cost + labor_cost
    return PricingResult(
        machine_time_cost=machine_time_cost,
        material_cost=material_cost,
        labor_cost=labor_cost,
        total_price=total_price,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_costing_price.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full costing test suite**

Run: `pytest tests/test_costing_time.py tests/test_costing_material.py tests/test_costing_price.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add waterjet_quoter/costing.py tests/test_costing_price.py
git commit -m "Add price calculation with machine/material/labor breakdown"
```

---

## Task 11: reporting.py — structured output and human-readable report

**Files:**
- Create: `waterjet_quoter/reporting.py`
- Test: `tests/test_reporting.py`

**Interfaces:**
- Consumes: `CuttingTimeResult`, `MaterialEstimateResult`, `PricingResult`, `PieceQuote` from Tasks 8-10
- Produces: `build_result_dict(input_meta: dict, cutting_time: CuttingTimeResult, material_estimate: MaterialEstimateResult, pricing: PricingResult, geometry_warnings: List[str]) -> dict`, `print_report(result: dict) -> None`, `to_json(result: dict) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reporting.py
import json

from waterjet_quoter.costing import (
    PieceQuote,
    CuttingTimeResult,
    MaterialEstimateResult,
    PricingResult,
)
from waterjet_quoter.reporting import build_result_dict, print_report, to_json


def _sample_result():
    cutting_time = CuttingTimeResult(
        pieces=[
            PieceQuote(
                piece_id=0,
                cut_length_in=35.14,
                pierce_count=2,
                bbox_width_in=10.0,
                bbox_height_in=6.0,
                area_in2=60.0,
                unit_time_min=2.53,
            )
        ],
        total_time_min=126.5,
    )
    material_estimate = MaterialEstimateResult(
        total_area_in2=3000.0,
        sheets_needed=2,
        utilization_factor=0.75,
        warnings=[],
    )
    pricing = PricingResult(
        machine_time_cost=263.5,
        material_cost=440.0,
        labor_cost=105.0,
        total_price=808.5,
    )
    input_meta = {
        "file": "plate.dxf",
        "material": "aluminum",
        "thickness": "6mm",
        "quality": "standard",
        "quantity": 50,
    }
    return build_result_dict(input_meta, cutting_time, material_estimate, pricing, [])


def test_build_result_dict_has_expected_shape():
    result = _sample_result()

    assert result["input"]["material"] == "aluminum"
    assert result["pieces"][0]["cut_length_in"] == 35.14
    assert result["cutting_time"]["total_time_min"] == 126.5
    assert result["cutting_time"]["quantity"] == 50
    assert result["material_estimate"]["sheets_needed"] == 2
    assert result["pricing"]["total_price"] == 808.5
    assert result["geometry_warnings"] == []


def test_to_json_round_trips():
    result = _sample_result()
    text = to_json(result)
    parsed = json.loads(text)
    assert parsed["pricing"]["total_price"] == 808.5


def test_print_report_includes_key_figures(capsys):
    result = _sample_result()
    print_report(result)
    captured = capsys.readouterr()
    assert "aluminum" in captured.out
    assert "808.50" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporting.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.reporting'`

- [ ] **Step 3: Write reporting.py**

```python
# waterjet_quoter/reporting.py
"""Formats the quote result: human-readable text and structured dict/JSON."""
import json
from dataclasses import asdict
from typing import List

from .costing import CuttingTimeResult, MaterialEstimateResult, PricingResult


def build_result_dict(
    input_meta: dict,
    cutting_time: CuttingTimeResult,
    material_estimate: MaterialEstimateResult,
    pricing: PricingResult,
    geometry_warnings: List[str],
) -> dict:
    return {
        "input": input_meta,
        "pieces": [asdict(p) for p in cutting_time.pieces],
        "cutting_time": {
            "quantity": input_meta["quantity"],
            "total_time_min": cutting_time.total_time_min,
        },
        "material_estimate": {
            "total_area_in2": material_estimate.total_area_in2,
            "sheets_needed": material_estimate.sheets_needed,
            "utilization_factor": material_estimate.utilization_factor,
            "warnings": material_estimate.warnings,
        },
        "pricing": asdict(pricing),
        "geometry_warnings": geometry_warnings,
    }


def print_report(result: dict) -> None:
    inp = result["input"]
    print("=== Soumission waterjet ===")
    print(f"Fichier: {inp['file']}")
    print(f"Matériau: {inp['material']} {inp['thickness']} (finition: {inp['quality']})")
    print(f"Quantité: {inp['quantity']}")
    print()
    print("--- Pièces ---")
    for piece in result["pieces"]:
        print(
            f"  Pièce {piece['piece_id']}: longueur de coupe "
            f"{piece['cut_length_in']:.2f} po, {piece['pierce_count']} perçage(s), "
            f"bbox {piece['bbox_width_in']:.2f}x{piece['bbox_height_in']:.2f} po, "
            f"temps unitaire {piece['unit_time_min']:.2f} min"
        )
    print()
    ct = result["cutting_time"]
    print(
        f"Temps de coupe total: {ct['total_time_min']:.2f} min "
        f"(pour {ct['quantity']} exemplaire(s))"
    )
    print()
    me = result["material_estimate"]
    print(
        f"Feuilles nécessaires: {me['sheets_needed']} "
        f"(aire totale {me['total_area_in2']:.1f} po², "
        f"facteur d'utilisation {me['utilization_factor']})"
    )
    for w in me["warnings"]:
        print(f"  AVERTISSEMENT: {w}")
    for w in result["geometry_warnings"]:
        print(f"  AVERTISSEMENT: {w}")
    print()
    pr = result["pricing"]
    print("--- Prix ---")
    print(f"  Temps machine: ${pr['machine_time_cost']:.2f}")
    print(f"  Matière:       ${pr['material_cost']:.2f}")
    print(f"  Main-d'œuvre:  ${pr['labor_cost']:.2f}")
    print(f"  TOTAL:         ${pr['total_price']:.2f}")


def to_json(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporting.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add waterjet_quoter/reporting.py tests/test_reporting.py
git commit -m "Add human-readable report and structured JSON output"
```

---

## Task 12: main.py — CLI wiring and end-to-end integration

**Files:**
- Create: `waterjet_quoter/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `load_dxf` (Task 3), `extract_pieces`/`ExtractionResult` (Task 7), `lookup`/`MaterialNotFoundError` (Task 2), `compute_cutting_time`/`estimate_material`/`compute_price` (Tasks 8-10), `build_result_dict`/`print_report`/`to_json` (Task 11), `make_test_plate` (Task 4)
- Produces: `build_arg_parser() -> argparse.ArgumentParser`, `run(dxf_path: str, material: str, thickness: str, quality: str, qty: int) -> dict`, `main(argv=None) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_main.py
import pytest

from waterjet_quoter.make_test_dxf import make_test_plate
from waterjet_quoter.materials import MaterialNotFoundError
from waterjet_quoter.main import run, main


def test_run_end_to_end_matches_expected_test_plate_values(tmp_path):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    result = run(str(dxf_path), material="aluminum", thickness="6mm", quality="standard", qty=50)

    assert len(result["pieces"]) == 1
    piece = result["pieces"][0]
    assert piece["cut_length_in"] == pytest.approx(35.14, abs=0.05)
    assert piece["pierce_count"] == 2
    assert piece["bbox_width_in"] == pytest.approx(10.0, abs=1e-6)
    assert piece["bbox_height_in"] == pytest.approx(6.0, abs=1e-6)
    assert result["cutting_time"]["quantity"] == 50
    assert result["pricing"]["total_price"] > 0


def test_run_raises_for_unknown_material_thickness(tmp_path):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    with pytest.raises(MaterialNotFoundError):
        run(str(dxf_path), material="titanium", thickness="6mm", quality="standard", qty=1)


def test_main_cli_success_exit_code(tmp_path, capsys):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    exit_code = main([str(dxf_path), "--material", "aluminum", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "TOTAL" in captured.out


def test_main_cli_missing_material_exit_code(tmp_path, capsys):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    exit_code = main([str(dxf_path), "--material", "titanium", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur" in captured.err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'waterjet_quoter.main'`

- [ ] **Step 3: Write main.py**

```python
# waterjet_quoter/main.py
"""CLI entry point: parse arguments, run the pipeline, print the result."""
import argparse
import sys

from .costing import compute_cutting_time, estimate_material, compute_price
from .geometry import extract_pieces
from .ingestion import load_dxf
from .materials import lookup, MaterialNotFoundError
from .reporting import build_result_dict, print_report, to_json


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estime une soumission de découpe waterjet à partir d'un DXF."
    )
    parser.add_argument("dxf_path", help="Chemin vers le fichier DXF")
    parser.add_argument("--material", required=True, help="Nom du matériau (ex: aluminum)")
    parser.add_argument("--thickness", required=True, help="Épaisseur (ex: 6mm)")
    parser.add_argument("--quality", default="standard", help="Niveau de finition (défaut: standard)")
    parser.add_argument("--qty", type=int, default=1, help="Quantité commandée (défaut: 1)")
    parser.add_argument("--json", action="store_true", help="Affiche uniquement la sortie JSON")
    return parser


def run(dxf_path: str, material: str, thickness: str, quality: str, qty: int) -> dict:
    drawing = load_dxf(dxf_path)
    extraction = extract_pieces(drawing)
    material_params = lookup(material, thickness, quality)

    cutting_time = compute_cutting_time(extraction.pieces, material_params, qty)
    material_estimate = estimate_material(extraction.pieces, qty)
    pricing = compute_price(cutting_time.total_time_min, material_estimate.sheets_needed, material)

    input_meta = {
        "file": dxf_path,
        "material": material,
        "thickness": thickness,
        "quality": quality,
        "quantity": qty,
    }
    return build_result_dict(input_meta, cutting_time, material_estimate, pricing, extraction.warnings)


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        result = run(args.dxf_path, args.material, args.thickness, args.quality, args.qty)
    except MaterialNotFoundError as e:
        print(f"Erreur: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"Erreur: fichier introuvable: {args.dxf_path}", file=sys.stderr)
        return 1

    if args.json:
        print(to_json(result))
    else:
        print_report(result)
        print()
        print("--- JSON structuré ---")
        print(to_json(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the entire test suite**

Run: `pytest -v`
Expected: PASS (all tests across all modules)

- [ ] **Step 6: Manually verify against the test plate**

```bash
python -m waterjet_quoter.make_test_dxf
python -m waterjet_quoter.main test_plate.dxf --material aluminum --thickness 6mm --qty 50
```

Expected: report shows 1 piece, cut length ≈ 35.14 in, 2 pierces, bbox 10x6 in, plus a full price breakdown, followed by the structured JSON.

- [ ] **Step 7: Commit**

```bash
git add waterjet_quoter/main.py tests/test_main.py
git commit -m "Add CLI entry point wiring the full quoting pipeline"
```

---

## Post-implementation check

After Task 12, confirm every spec requirement has a home:
- File ingestion boundary → Task 3 (`ingestion.py`)
- Geometry extraction (cut length, pierce count, bbox/area) for LINE/ARC/CIRCLE/LWPOLYLINE/POLYLINE/SPLINE → Tasks 5-7
- Materials table loaded from JSON, explicit error on missing triplet → Task 2
- Cutting time aggregated by piece type with unit/qty/total shown → Task 8, surfaced in Task 11
- Material estimate with configurable utilization factor and large-piece warning → Task 9
- Price breakdown (machine/material/labor) with adjustable config → Task 10
- CLI + human-readable output + structured dict/JSON → Tasks 11-12
- Test DXF with documented expected values → Task 4, validated end-to-end in Task 12
