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
