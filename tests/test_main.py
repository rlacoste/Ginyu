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


def test_main_cli_malformed_dxf_exit_code(tmp_path, capsys):
    dxf_path = tmp_path / "garbage.dxf"
    dxf_path.write_bytes(b"not a real dxf file\nrandom garbage bytes\n")

    exit_code = main([str(dxf_path), "--material", "aluminum", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur" in captured.err


def test_main_cli_zero_qty_rejected(tmp_path, capsys):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    exit_code = main(
        [str(dxf_path), "--material", "aluminum", "--thickness", "6mm", "--qty", "0"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur" in captured.err


def test_main_cli_config_desync_reports_clean_error(tmp_path, capsys, monkeypatch):
    """Regression: if a material is in materials.json (so lookup() succeeds)
    but missing from config.SHEET_COST_BY_MATERIAL, compute_price() now
    raises materials.MaterialNotFoundError instead of a bare KeyError, so
    it's caught by main()'s existing MaterialNotFoundError handler with a
    clean (non-repr'd) message instead of a raw traceback.
    """
    from waterjet_quoter import config

    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))
    monkeypatch.delitem(config.SHEET_COST_BY_MATERIAL, "aluminum")

    exit_code = main([str(dxf_path), "--material", "aluminum", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur:" in captured.err
    # Must go through the MaterialNotFoundError path (clean __str__), not a
    # bare KeyError repr'd into the message with a stray quote.
    assert '"No sheet cost' not in captured.err
    assert "No sheet cost configured for material 'aluminum'" in captured.err


def test_main_cli_truncated_dxf_does_not_raise_stopiteration(tmp_path, capsys):
    """Regression: a truncated DXF file causes ezdxf's internal tagger to
    raise a bare StopIteration from ezdxf.readfile(), which isn't an
    ezdxf.DXFError or OSError subclass and previously escaped main()'s
    exception handling entirely, producing a raw traceback.
    """
    dxf_path = tmp_path / "truncated.dxf"
    dxf_path.write_text("0\nSECTION\n2\nHEADER\n")

    exit_code = main([str(dxf_path), "--material", "aluminum", "--thickness", "6mm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur" in captured.err


def test_main_cli_negative_qty_rejected(tmp_path, capsys):
    dxf_path = tmp_path / "plate.dxf"
    make_test_plate(str(dxf_path))

    exit_code = main(
        [str(dxf_path), "--material", "aluminum", "--thickness", "6mm", "--qty", "-5"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erreur" in captured.err
