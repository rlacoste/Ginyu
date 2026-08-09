import csv

import pytest

from waterjet_quoter.list_materials import (
    rows_from_table,
    print_table,
    write_csv,
    main,
)

SAMPLE_TABLE = {
    "Aluminium": {
        0.25: {"6061 T6": {"feed_rate_ipm": 90.424}, "5052": {"feed_rate_ipm": 85.0}},
        1.0: {"6061 T6": {"feed_rate_ipm": 18.288}},
    },
    "Mild Steel": {
        0.125: {"A1008": {"feed_rate_ipm": 60.0}},
    },
}


def test_rows_from_table_flattens_and_sorts():
    rows = rows_from_table(SAMPLE_TABLE)

    assert len(rows) == 4
    assert rows == sorted(rows)
    assert ("Aluminium", "6061 T6", 0.25, 90.424) in rows
    assert ("Aluminium", "5052", 0.25, 85.0) in rows
    assert ("Aluminium", "6061 T6", 1.0, 18.288) in rows
    assert ("Mild Steel", "A1008", 0.125, 60.0) in rows


def test_rows_from_table_filters_by_material_case_insensitive():
    rows = rows_from_table(SAMPLE_TABLE, material_filter="aluminium")

    assert len(rows) == 3
    assert all(r[0] == "Aluminium" for r in rows)


def test_rows_from_table_filter_matches_nothing():
    rows = rows_from_table(SAMPLE_TABLE, material_filter="titanium")

    assert rows == []


def test_print_table_includes_header_and_rows(capsys):
    rows = rows_from_table(SAMPLE_TABLE, material_filter="Mild Steel")

    print_table(rows)

    captured = capsys.readouterr()
    assert "Mild Steel" in captured.out
    assert "A1008" in captured.out
    assert "1 entrée" in captured.out


def test_print_table_handles_empty_rows(capsys):
    print_table([])

    captured = capsys.readouterr()
    assert "Aucun matériau" in captured.out


def test_write_csv_round_trips(tmp_path):
    rows = rows_from_table(SAMPLE_TABLE, material_filter="Mild Steel")
    csv_path = tmp_path / "materials_reference.csv"

    write_csv(rows, str(csv_path))

    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        data_rows = list(reader)
    assert header == ["material", "quality", "thickness_in", "feed_rate_ipm"]
    assert data_rows == [["Mild Steel", "A1008", "0.125", "60.0"]]


def test_main_prints_to_stdout_by_default(monkeypatch, capsys):
    monkeypatch.setattr(
        "waterjet_quoter.list_materials.load_table", lambda *a, **k: SAMPLE_TABLE
    )

    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Aluminium" in captured.out
    assert "4 entrée" in captured.out


def test_main_writes_csv_when_requested(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "waterjet_quoter.list_materials.load_table", lambda *a, **k: SAMPLE_TABLE
    )
    csv_path = tmp_path / "out.csv"

    exit_code = main(["--csv", str(csv_path)])

    assert exit_code == 0
    assert csv_path.exists()
    with open(csv_path, newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 5  # header + 4 data rows


def test_main_applies_material_filter(monkeypatch, capsys):
    monkeypatch.setattr(
        "waterjet_quoter.list_materials.load_table", lambda *a, **k: SAMPLE_TABLE
    )

    exit_code = main(["--material", "Mild"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Aluminium" not in captured.out
    assert "Mild Steel" in captured.out
