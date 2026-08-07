"""Loads and looks up the materials reference table (feed rate; pierce time
is derived from it, see lookup()).

The table lives in a Postgres `materials` table (see db.py, db/schema.sql),
indexed by material -> thickness_in -> quality (quality here means the
alloy/grade, e.g. "6061 T6", not a cut-finish level -- iGEMS does not track
cut-finish tiers separately). This module only knows how to read that table
and look values up; costing.py never queries the database directly.
"""
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from . import config
from .db import get_connection

_THICKNESS_PRECISION = 4


class MaterialNotFoundError(KeyError):
    """Raised when a (material, thickness, quality) triplet is not in the table."""

    def __str__(self):
        return self.args[0] if self.args else ""


@dataclass(frozen=True)
class MaterialParams:
    feed_rate_ipm: float
    pierce_time_sec: float


def _normalize_thickness(thickness: float) -> float:
    return round(float(thickness), _THICKNESS_PRECISION)


def _rows_to_table(rows: Iterable[Tuple[str, str, float, float]]) -> dict:
    """Build the nested material -> thickness -> quality -> params dict.

    Each row is (material, quality, thickness_in, feed_rate_ipm).
    """
    table: dict = {}
    for material, quality, thickness_in, feed_rate_ipm in rows:
        thickness_key = _normalize_thickness(thickness_in)
        table.setdefault(material, {}).setdefault(thickness_key, {})[quality] = {
            "feed_rate_ipm": float(feed_rate_ipm),
        }
    return table


def load_table(conn=None) -> dict:
    """Load the full materials table from Postgres.

    Pass `conn` (an existing psycopg connection) to reuse a connection you
    already opened; otherwise one is opened and closed here.
    """
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT material, quality, thickness_in, feed_rate_ipm FROM materials"
            )
            rows = cur.fetchall()
    finally:
        if owns_conn:
            conn.close()
    return _rows_to_table(rows)


def lookup(
    material: str,
    thickness: float,
    quality: str,
    table: Optional[dict] = None,
) -> MaterialParams:
    if table is None:
        table = load_table()

    if material not in table:
        raise MaterialNotFoundError(
            f"Matériau inconnu: {material!r}. Matériaux disponibles: "
            f"{sorted(table.keys())}."
        )

    thickness_key = _normalize_thickness(thickness)
    thicknesses_for_material = table[material]
    if thickness_key not in thicknesses_for_material:
        available = sorted(thicknesses_for_material.keys())
        raise MaterialNotFoundError(
            f"Aucune entrée pour {material!r} à l'épaisseur {thickness!r} po. "
            f"Épaisseurs disponibles: {available}."
        )

    qualities_for_thickness = thicknesses_for_material[thickness_key]
    if quality not in qualities_for_thickness:
        available_qualities = sorted(qualities_for_thickness.keys())
        raise MaterialNotFoundError(
            f"Aucune entrée pour {material!r} à {thickness!r} po avec le "
            f"grade {quality!r}. Grades disponibles à cette épaisseur: "
            f"{available_qualities}."
        )

    feed_rate_ipm = qualities_for_thickness[quality]["feed_rate_ipm"]
    pierce_time_sec = config.PIERCE_TIME_CALIBRATION_CONSTANT / feed_rate_ipm
    return MaterialParams(feed_rate_ipm=feed_rate_ipm, pierce_time_sec=pierce_time_sec)
