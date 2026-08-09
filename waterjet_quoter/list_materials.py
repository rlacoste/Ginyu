"""Reference tool: lists material/quality/thickness/feed-rate combinations
from the materials table, so real --material/--thickness/--quality values
for waterjet_quoter.main can be looked up instead of guessed.

Usage:
  python -m waterjet_quoter.list_materials
  python -m waterjet_quoter.list_materials --material Aluminium
  python -m waterjet_quoter.list_materials --csv materials_reference.csv
"""
import argparse
import csv
import sys
from typing import List, Optional, Tuple

from .materials import load_table

Row = Tuple[str, str, float, float]


def rows_from_table(table: dict, material_filter: Optional[str] = None) -> List[Row]:
    rows: List[Row] = []
    for material, thicknesses in table.items():
        if material_filter and material_filter.lower() not in material.lower():
            continue
        for thickness_in, qualities in thicknesses.items():
            for quality, params in qualities.items():
                rows.append((material, quality, thickness_in, params["feed_rate_ipm"]))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return rows


def print_table(rows: List[Row]) -> None:
    if not rows:
        print("Aucun matériau trouvé.")
        return
    header = f"{'Matériau':<25} {'Grade':<20} {'Épaisseur (po)':>15} {'Vitesse (po/min)':>18}"
    print(header)
    print("-" * len(header))
    for material, quality, thickness_in, feed_rate_ipm in rows:
        print(f"{material:<25} {quality:<20} {thickness_in:>15.4f} {feed_rate_ipm:>18.3f}")
    print(f"\n{len(rows)} entrée(s).")


def write_csv(rows: List[Row], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["material", "quality", "thickness_in", "feed_rate_ipm"])
        writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Liste les matériaux/grades/épaisseurs disponibles dans la table."
    )
    parser.add_argument(
        "--material",
        default=None,
        help="Filtre par matériau (sous-chaîne, insensible à la casse)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Écrit le résultat dans ce fichier CSV au lieu de l'afficher",
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    table = load_table()
    rows = rows_from_table(table, material_filter=args.material)

    if args.csv:
        write_csv(rows, args.csv)
        print(f"{len(rows)} entrée(s) écrite(s) dans {args.csv}")
    else:
        print_table(rows)

    return 0


if __name__ == "__main__":
    sys.exit(main())
