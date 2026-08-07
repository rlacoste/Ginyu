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

# Contours whose total perimeter falls below this (inches) are treated as
# degenerate drawing artefacts (e.g. a zero-length LINE, or a closed entity
# whose vertices all coincide) rather than real geometry, and are skipped
# with a warning instead of being counted as a piece.
_MIN_CONTOUR_LENGTH_IN = 1e-6


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
    if dxftype == "SPLINE":
        return bool(entity.closed)
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

        # Forward extension: extend from chain[-1]
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

        # Backward extension: extend from chain[0] if not yet closed
        if not (_snap(chain[-1], tolerance) == start_key and len(chain) > 1):
            progressed = True
            while progressed:
                progressed = False
                current_key = _snap(chain[0], tolerance)
                if current_key == _snap(chain[-1], tolerance) and len(chain) > 1:
                    break
                for i, idx in enumerate(remaining):
                    seg = segments[idx]
                    if _snap(seg[-1], tolerance) == current_key:
                        chain = seg[:-1] + chain
                        remaining.pop(i)
                        progressed = True
                        break
                    if _snap(seg[0], tolerance) == current_key:
                        chain = list(reversed(seg))[:-1] + chain
                        remaining.pop(i)
                        progressed = True
                        break

        if _snap(chain[-1], tolerance) == _snap(chain[0], tolerance) and len(chain) > 1:
            closed_contours.append(chain)
        else:
            incomplete_contours.append(chain)

    return ChainResult(closed_contours, incomplete_contours)


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
            if parent_idx is not None and parent_idx in pieces_by_outer_index:
                pieces_by_outer_index[parent_idx].contours.append(contours[i])
            else:
                # Fallback: if no parent can be determined (depth inflation from
                # unrelated overlaps or parent is itself a child), treat as independent piece
                piece = Piece(piece_id=next_id, contours=[contours[i]])
                pieces_by_outer_index[i] = piece
                pieces.append(piece)
                next_id += 1

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
    warnings: List[str] = []

    for entity in msp:
        if entity.dxftype() not in SUPPORTED_DXFTYPES:
            continue
        try:
            points = flatten_entity(entity, flattening_distance)
        except (TypeError, ValueError, IndexError) as exc:
            warnings.append(
                f"Entité {entity.dxftype()} ignorée : géométrie non exploitable ({exc})."
            )
            continue
        if len(points) < 2:
            warnings.append(
                f"Entité {entity.dxftype()} ignorée : géométrie non exploitable "
                f"(pas assez de points après aplatissement)."
            )
            continue
        if is_entity_closed(entity):
            if points[0] != points[-1]:
                points = points + [points[0]]
            if polyline_length(points) < _MIN_CONTOUR_LENGTH_IN:
                warnings.append(
                    "Contour de longueur quasi nulle ignoré (probable artefact de dessin)."
                )
                continue
            closed_contours.append(Contour(points=points))
        else:
            open_segments.append(points)

    if open_segments:
        chain_result = chain_open_segments(open_segments, chaining_tolerance)
        for chain in chain_result.closed_contours:
            if polyline_length(chain) < _MIN_CONTOUR_LENGTH_IN:
                warnings.append(
                    "Contour de longueur quasi nulle ignoré (probable artefact de dessin)."
                )
                continue
            closed_contours.append(Contour(points=chain))
        for incomplete in chain_result.incomplete_contours:
            warnings.append(
                f"Contour incomplet détecté ({len(incomplete)} points) — "
                f"segments non refermés en boucle, exclu du calcul."
            )

    pieces = group_contours_into_pieces(closed_contours)
    if not pieces:
        warnings.append(
            "Aucune pièce exploitable détectée dans ce DXF — vérifier le fichier source."
        )
    return ExtractionResult(pieces=pieces, warnings=warnings)
