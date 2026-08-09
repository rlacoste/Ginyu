"""Sets or updates a material's dynamic price in the material_prices table.

Manual seeding/update path for the dynamic-pricing table (see
db/schema.sql, waterjet_quoter/material_prices.py) until a weekly or other
automated ingestion source exists.

Usage:
  python -m waterjet_quoter.set_material_price --material Copper --price-per-lb 4.50 --machine-rate-multiplier 2.0
  python -m waterjet_quoter.set_material_price --material Aluminium --price-per-lb 1.85
"""
import argparse
import sys

from .db import get_connection


def set_price(
    material: str, price_per_lb: float, machine_rate_multiplier: float, conn=None
) -> None:
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into material_prices (material, price_per_lb, machine_rate_multiplier, updated_at)
                values (%s, %s, %s, now())
                on conflict (material)
                do update set price_per_lb = excluded.price_per_lb,
                              machine_rate_multiplier = excluded.machine_rate_multiplier,
                              updated_at = now()
                """,
                (material, price_per_lb, machine_rate_multiplier),
            )
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ajoute ou met à jour le prix d'un matériau dans material_prices."
    )
    parser.add_argument("--material", required=True, help="Nom exact du matériau (ex: Copper)")
    parser.add_argument(
        "--price-per-lb", required=True, type=float, help="Prix de la matière première en $/lb"
    )
    parser.add_argument(
        "--machine-rate-multiplier",
        type=float,
        default=1.0,
        help="Multiplicateur appliqué à MACHINE_RATE_PER_HOUR pour ce matériau (défaut: 1.0)",
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    set_price(args.material, args.price_per_lb, args.machine_rate_multiplier)
    print(
        f"{args.material}: price_per_lb=${args.price_per_lb:.2f}, "
        f"machine_rate_multiplier={args.machine_rate_multiplier:.2f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
