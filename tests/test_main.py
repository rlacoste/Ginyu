import pytest

from waterjet_quoter.make_test_dxf import make_test_plate
from waterjet_quoter.materials import MaterialNotFoundError
from waterjet_quoter.main import run, main


def test_run_end_to_end_matches_expected_test_plate_values(tmp_path):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    result = run(str(dxf_path), material="aluminum", thickness="6mm", quality="standard", qty=50)

    assert len(result["pieces"]) == 1
    piece = result["pieces"][0]
    assert piece["cut_length_in"] == pytest.approx(35.14, abs=0.05)
    assert piece["pierce_count"] == 2
    assert piece["bbox_width_in"] == pytest.approx(10.0, abs=1e-6)
    assert piece["bbox_height_in"] == pytest.approx(6.0, abs=1e-6)
    assert result["cutting_time"]["quantity"] == 50
    assert result["pricing"]["total_price"] > 0


def test_run_raises_for_unknown_material_thickness(tmp_path):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    with pytest.raises(MaterialNotFoundError):
        run(str(dxf_path), material="titanium", thickness="6mm", quality="standard", qty=1)


def test_main_cli_success_exit_code(tmp_path, capsys):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    exit_code = main([str(dxf_path), "--material", "aluminum", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "TOTAL" in captured.out


def test_main_cli_missing_material_exit_code(tmp_path, capsys):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    exit_code = main([str(dxf_path), "--material", "titanium", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur" in captured.err
