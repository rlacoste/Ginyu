"""Formats the quote result: human-readable text and structured dict/JSON."""
import json
from dataclasses import asdict
from typing import List

from .costing import CuttingTimeResult, MaterialEstimateResult, PricingResult


def build_result_dict(
    input_meta: dict,
    cutting_time: CuttingTimeResult,
    material_estimate: MaterialEstimateResult,
    pricing: PricingResult,
    geometry_warnings: List[str],
) -> dict:
    return {
        "input": input_meta,
        "pieces": [asdict(p) for p in cutting_time.pieces],
        "cutting_time": {
            "quantity": input_meta["quantity"],
            "total_time_min": cutting_time.total_time_min,
        },
        "material_estimate": {
            "total_area_in2": material_estimate.total_area_in2,
            "sheets_needed": material_estimate.sheets_needed,
            "utilization_factor": material_estimate.utilization_factor,
            "warnings": material_estimate.warnings,
        },
        "pricing": asdict(pricing),
        "geometry_warnings": geometry_warnings,
    }


def print_report(result: dict) -> None:
    inp = result["input"]
    print("=== Soumission waterjet ===")
    print(f"Fichier: {inp['file']}")
    print(f"Matériau: {inp['material']} {inp['thickness']}po (grade: {inp['quality']})")
    print(f"Quantité: {inp['quantity']}")
    print()
    print("--- Pièces ---")
    for piece in result["pieces"]:
        print(
            f"  Pièce {piece['piece_id']}: longueur de coupe "
            f"{piece['cut_length_in']:.2f} po, {piece['pierce_count']} perçage(s), "
            f"bbox {piece['bbox_width_in']:.2f}x{piece['bbox_height_in']:.2f} po, "
            f"temps unitaire {piece['unit_time_min']:.2f} min"
        )
    print()
    ct = result["cutting_time"]
    print(
        f"Temps de coupe total: {ct['total_time_min']:.2f} min "
        f"(pour {ct['quantity']} exemplaire(s))"
    )
    print()
    me = result["material_estimate"]
    print(
        f"Feuilles nécessaires: {me['sheets_needed']} "
        f"(aire totale {me['total_area_in2']:.1f} po², "
        f"facteur d'utilisation {me['utilization_factor']})"
    )
    for w in me["warnings"]:
        print(f"  AVERTISSEMENT: {w}")
    for w in result["geometry_warnings"]:
        print(f"  AVERTISSEMENT: {w}")
    print()
    pr = result["pricing"]
    print("--- Prix ---")
    print(f"  Temps machine: ${pr['machine_time_cost']:.2f}")
    print(f"  Matière:       ${pr['material_cost']:.2f}")
    print(f"  Main-d'œuvre:  ${pr['labor_cost']:.2f}")
    print(f"  TOTAL:         ${pr['total_price']:.2f}")


def to_json(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False)
