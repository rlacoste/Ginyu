"""Cutting time, material estimate, and price calculations."""
import math
from dataclasses import dataclass
from typing import List, Optional

from . import config
from .geometry import Piece
from .materials import MaterialNotFoundError, MaterialParams
from .material_prices import lookup_price

# 1 kg/m^3 expressed in lb/in^3 (1 kg = 2.2046226218 lb, 1 m^3 = 61023.7441 in^3).
KG_PER_M3_TO_LB_PER_IN3 = 3.612729e-5


@dataclass
class PieceQuote:
    piece_id: int
    cut_length_in: float
    pierce_count: int
    bbox_width_in: float
    bbox_height_in: float
    area_in2: float
    unit_time_min: float


@dataclass
class CuttingTimeResult:
    pieces: List[PieceQuote]
    total_time_min: float


def compute_cutting_time(
    pieces: List[Piece], material: MaterialParams, quantity: int
) -> CuttingTimeResult:
    piece_quotes = []
    total_time_min = 0.0
    for piece in pieces:
        width, height = piece.bbox
        unit_time_min = piece.cut_length_in / material.feed_rate_ipm
        total_time_min += unit_time_min * quantity
        piece_quotes.append(
            PieceQuote(
                piece_id=piece.piece_id,
                cut_length_in=piece.cut_length_in,
                pierce_count=piece.pierce_count,
                bbox_width_in=width,
                bbox_height_in=height,
                area_in2=piece.area_in2,
                unit_time_min=unit_time_min,
            )
        )
    return CuttingTimeResult(pieces=piece_quotes, total_time_min=total_time_min)


@dataclass
class MaterialEstimateResult:
    total_area_in2: float
    sheets_needed: int
    utilization_factor: float
    warnings: List[str]


def estimate_material(pieces: List[Piece], quantity: int) -> MaterialEstimateResult:
    warnings = []
    total_area_in2 = 0.0
    for piece in pieces:
        width, height = piece.bbox
        total_area_in2 += piece.area_in2 * quantity
        if max(width, height) > config.LARGE_PIECE_DIMENSION_THRESHOLD_IN:
            warnings.append(
                f"Pièce {piece.piece_id}: dimension max "
                f"{max(width, height):.1f} po dépasse le seuil de "
                f"{config.LARGE_PIECE_DIMENSION_THRESHOLD_IN} po — nesting "
                f"manuel recommandé — estimation matière peu fiable pour "
                f"cette pièce."
            )

    sheet_area_in2 = config.SHEET_WIDTH_IN * config.SHEET_HEIGHT_IN
    usable_area_in2 = sheet_area_in2 * config.NESTING_UTILIZATION_FACTOR
    sheets_needed = (
        math.ceil(total_area_in2 / usable_area_in2) if total_area_in2 > 0 else 0
    )

    return MaterialEstimateResult(
        total_area_in2=total_area_in2,
        sheets_needed=sheets_needed,
        utilization_factor=config.NESTING_UTILIZATION_FACTOR,
        warnings=warnings,
    )


@dataclass
class PricingResult:
    machine_time_cost: float
    material_cost: float
    labor_cost: float
    total_price: float


def compute_price(
    total_time_min: float,
    net_area_in2: float,
    thickness_in: float,
    material: str,
    price_table: Optional[dict] = None,
) -> PricingResult:
    """Price a job from net part area (not full sheets -- offcuts are kept
    and nested into on later jobs rather than charged per-job) plus machine
    time at a material-specific rate.
    """
    if material not in config.DENSITY_KG_PER_M3:
        raise MaterialNotFoundError(
            f"Aucune densité configurée pour le matériau {material!r} dans "
            f"config.DENSITY_KG_PER_M3."
        )
    price_params = lookup_price(material, table=price_table)

    density_lb_per_in3 = config.DENSITY_KG_PER_M3[material] * KG_PER_M3_TO_LB_PER_IN3
    weight_lb = net_area_in2 * thickness_in * density_lb_per_in3
    material_cost = (
        weight_lb * price_params.price_per_lb * config.MATERIAL_COST_ADJUSTMENT_FACTOR
    )

    effective_machine_rate = config.MACHINE_RATE_PER_HOUR * price_params.machine_rate_multiplier
    machine_time_cost = (total_time_min / 60.0) * effective_machine_rate

    labor_cost = sum(config.LABOR_FLAT_FEES.values())
    total_price = machine_time_cost + material_cost + labor_cost
    return PricingResult(
        machine_time_cost=machine_time_cost,
        material_cost=material_cost,
        labor_cost=labor_cost,
        total_price=total_price,
    )
