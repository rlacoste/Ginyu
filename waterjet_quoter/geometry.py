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
