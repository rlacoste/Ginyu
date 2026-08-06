import json

from waterjet_quoter.costing import (
    PieceQuote,
    CuttingTimeResult,
    MaterialEstimateResult,
    PricingResult,
)
from waterjet_quoter.reporting import build_result_dict, print_report, to_json


def _sample_result():
    cutting_time = CuttingTimeResult(
        pieces=[
            PieceQuote(
                piece_id=0,
                cut_length_in=35.14,
                pierce_count=2,
                bbox_width_in=10.0,
                bbox_height_in=6.0,
                area_in2=60.0,
                unit_time_min=2.53,
            )
        ],
        total_time_min=126.5,
    )
    material_estimate = MaterialEstimateResult(
        total_area_in2=3000.0,
        sheets_needed=2,
        utilization_factor=0.75,
        warnings=[],
    )
    pricing = PricingResult(
        machine_time_cost=263.5,
        material_cost=440.0,
        labor_cost=105.0,
        total_price=808.5,
    )
    input_meta = {
        "file": "plate.dxf",
        "material": "aluminum",
        "thickness": "6mm",
        "quality": "standard",
        "quantity": 50,
    }
    return build_result_dict(input_meta, cutting_time, material_estimate, pricing, [])


def test_build_result_dict_has_expected_shape():
    result = _sample_result()

    assert result["input"]["material"] == "aluminum"
    assert result["pieces"][0]["cut_length_in"] == 35.14
    assert result["cutting_time"]["total_time_min"] == 126.5
    assert result["cutting_time"]["quantity"] == 50
    assert result["material_estimate"]["sheets_needed"] == 2
    assert result["pricing"]["total_price"] == 808.5
    assert result["geometry_warnings"] == []


def test_to_json_round_trips():
    result = _sample_result()
    text = to_json(result)
    parsed = json.loads(text)
    assert parsed["pricing"]["total_price"] == 808.5


def test_print_report_includes_key_figures(capsys):
    result = _sample_result()
    print_report(result)
    captured = capsys.readouterr()
    assert "aluminum" in captured.out
    assert "808.50" in captured.out
