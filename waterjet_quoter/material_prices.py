"""Loads and looks up dynamic material pricing (price per pound, machine
rate multiplier) from the Postgres `material_prices` table.

This is deliberately a separate table (and module) from materials.py's
cutting-parameter table: feed rate changes only when a new iGEMS export is
imported, while price_per_lb is expected to move frequently (weekly, or
per material as the shop's supplier costs change) -- keeping them apart
means updating a price never touches cutting-parameter data and vice
versa. Both tables key on the same `material` string so they join cleanly.
"""
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from .db import get_connection
from .materials import MaterialNotFoundError

Row = Tuple[str, float, float]


@dataclass(frozen=True)
class MaterialPriceParams:
    price_per_lb: float
    machine_rate_multiplier: float


def _rows_to_price_table(rows: Iterable[Row]) -> dict:
    """Build the material -> {price_per_lb, machine_rate_multiplier} dict.

    Each row is (material, price_per_lb, machine_rate_multiplier).
    """
    table: dict = {}
    for material, price_per_lb, machine_rate_multiplier in rows:
        table[material] = {
            "price_per_lb": float(price_per_lb),
            "machine_rate_multiplier": float(machine_rate_multiplier),
        }
    return table


def load_price_table(conn=None) -> dict:
    """Load the full material_prices table from Postgres.

    Pass `conn` (an existing psycopg connection) to reuse a connection you
    already opened; otherwise one is opened and closed here.
    """
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT material, price_per_lb, machine_rate_multiplier FROM material_prices"
            )
            rows = cur.fetchall()
    finally:
        if owns_conn:
            conn.close()
    return _rows_to_price_table(rows)


def lookup_price(material: str, table: Optional[dict] = None) -> MaterialPriceParams:
    if table is None:
        table = load_price_table()

    if material not in table:
        raise MaterialNotFoundError(
            f"Aucun prix configuré pour le matériau {material!r} dans "
            f"material_prices. Matériaux avec un prix: {sorted(table.keys())}. "
            f"Utilise python -m waterjet_quoter.set_material_price pour en ajouter un."
        )

    entry = table[material]
    return MaterialPriceParams(
        price_per_lb=entry["price_per_lb"],
        machine_rate_multiplier=entry["machine_rate_multiplier"],
    )
