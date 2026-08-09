"""Cutting time, material estimate, and price calculations."""
import math
from dataclasses import dataclass
from typing import List

from . import config
from .geometry import Piece
from .materials import MaterialNotFoundError, MaterialParams


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


def compute_price(total_time_min: float, sheets_needed: int, material: str) -> PricingResult:
    if material not in config.SHEET_COST_BY_MATERIAL:
        raise MaterialNotFoundError(
            f"No sheet cost configured for material {material!r} in "
            f"config.SHEET_COST_BY_MATERIAL."
        )
    machine_time_cost = (total_time_min / 60.0) * config.MACHINE_RATE_PER_HOUR
    material_cost = sheets_needed * config.SHEET_COST_BY_MATERIAL[material]
    labor_cost = sum(config.LABOR_FLAT_FEES.values())
    total_price = machine_time_cost + material_cost + labor_cost
    return PricingResult(
        machine_time_cost=machine_time_cost,
        material_cost=material_cost,
        labor_cost=labor_cost,
        total_price=total_price,
    )
