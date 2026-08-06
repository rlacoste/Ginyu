"""Cutting time, material estimate, and price calculations."""
import math
from dataclasses import dataclass
from typing import List

from . import config
from .geometry import Piece
from .materials import MaterialParams


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
        pierce_time_min = (piece.pierce_count * material.pierce_time_sec) / 60.0
        cut_time_min = piece.cut_length_in / material.feed_rate_ipm
        unit_time_min = cut_time_min + pierce_time_min
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
