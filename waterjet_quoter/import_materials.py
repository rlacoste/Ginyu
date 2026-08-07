"""Imports an iGEMS materials CSV export into the Postgres `materials` table.

Only four of the export's 100+ columns matter for this engine: Name,
Quality (the alloy/grade), Thickness (already in inches), and
*AWJFixedSpeed* (the abrasive-waterjet cutting feed rate, in/min -- every
row in the source export has *AWJAutomatic*=False, meaning iGEMS uses this
fixed value rather than computing speed dynamically). Everything else
(pressure, abrasive flow, TAC tables, other cutting technologies, ...) is
ignored.

Usage: python -m waterjet_quoter.import_materials <path-to-csv>
"""
import csv
import sys
from typing import List, Tuple

from .db import get_connection

Row = Tuple[str, str, float, float]


def parse_csv_rows(csv_path) -> List[Row]:
    """Extract (material, quality, thickness_in, feed_rate_ipm) rows.

    Rows with a missing, non-numeric, or non-positive feed rate are
    skipped -- there is nothing usable to import for them.
    """
    rows: List[Row] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for record in reader:
            feed_rate_raw = record.get("*AWJFixedSpeed*", "").strip()
            if not feed_rate_raw:
                continue
            try:
                feed_rate_ipm = float(feed_rate_raw)
            except ValueError:
                continue
            if feed_rate_ipm <= 0:
                continue

            material = record["Name"].strip()
            quality = record["Quality"].strip()
            thickness_in = round(float(record["Thickness"]), 4)
            rows.append((material, quality, thickness_in, feed_rate_ipm))
    return rows


def import_materials(csv_path, conn=None) -> int:
    """Upsert all parsed rows into the materials table. Returns row count."""
    rows = parse_csv_rows(csv_path)

    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into materials (material, quality, thickness_in, feed_rate_ipm)
                values (%s, %s, %s, %s)
                on conflict (material, quality, thickness_in)
                do update set feed_rate_ipm = excluded.feed_rate_ipm
                """,
                rows,
            )
        conn.commit()
    finally:
        if owns_conn:
            conn.close()
    return len(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m waterjet_quoter.import_materials <path-to-csv>", file=sys.stderr)
        sys.exit(2)
    count = import_materials(sys.argv[1])
    print(f"Imported {count} material rows.")
