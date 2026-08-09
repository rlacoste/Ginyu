"""CLI entry point: parse arguments, run the pipeline, print the result."""
import argparse
import sys

import ezdxf

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
    parser.add_argument(
        "--thickness", required=True, type=float, help="Épaisseur en pouces (ex: 0.25)"
    )
    parser.add_argument(
        "--quality",
        required=True,
        help="Alliage/grade du matériau (ex: 6061-T6) -- aucune valeur par défaut sensée",
    )
    parser.add_argument("--qty", type=int, default=1, help="Quantité commandée (défaut: 1)")
    parser.add_argument("--json", action="store_true", help="Affiche uniquement la sortie JSON")
    return parser


def run(dxf_path: str, material: str, thickness: float, quality: str, qty: int) -> dict:
    drawing = load_dxf(dxf_path)
    extraction = extract_pieces(drawing)
    material_params = lookup(material, thickness, quality)

    cutting_time = compute_cutting_time(extraction.pieces, material_params, qty)
    material_estimate = estimate_material(extraction.pieces, qty)
    pricing = compute_price(
        cutting_time.total_time_min, material_estimate.total_area_in2, thickness, material
    )

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

    if args.qty < 1:
        print(
            f"Erreur: la quantité doit être un entier positif (reçu: {args.qty})",
            file=sys.stderr,
        )
        return 1

    try:
        result = run(args.dxf_path, args.material, args.thickness, args.quality, args.qty)
    except MaterialNotFoundError as e:
        print(f"Erreur: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"Erreur: fichier introuvable: {args.dxf_path}", file=sys.stderr)
        return 1
    except ezdxf.DXFError as e:
        print(f"Erreur: fichier DXF invalide ou corrompu: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Erreur: impossible de lire le fichier {args.dxf_path}: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erreur inattendue ({type(e).__name__}): {e}", file=sys.stderr)
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
