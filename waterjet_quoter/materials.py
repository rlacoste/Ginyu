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
