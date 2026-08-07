import csv

from waterjet_quoter.import_materials import parse_csv_rows

FIELDNAMES = ["MachineType", "Name", "Quality", "Thickness", "*AWJFixedSpeed*", "*AWJAutomatic*"]


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_csv_rows_extracts_material_quality_thickness_feed_rate(tmp_path):
    csv_path = tmp_path / "materials.csv"
    _write_csv(
        csv_path,
        [
            {
                "MachineType": "0",
                "Name": "Aluminium",
                "Quality": "6061 T6",
                "Thickness": "0.2500",
                "*AWJFixedSpeed*": "90.424",
                "*AWJAutomatic*": "False",
            },
            {
                "MachineType": "0",
                "Name": "Mild Steel",
                "Quality": "A1008",
                "Thickness": "0.1250",
                "*AWJFixedSpeed*": "60.0",
                "*AWJAutomatic*": "False",
            },
        ],
    )

    rows = parse_csv_rows(csv_path)

    assert ("Aluminium", "6061 T6", 0.25, 90.424) in rows
    assert ("Mild Steel", "A1008", 0.125, 60.0) in rows


def test_parse_csv_rows_skips_blank_feed_rate(tmp_path):
    csv_path = tmp_path / "materials.csv"
    _write_csv(
        csv_path,
        [
            {
                "MachineType": "0",
                "Name": "Acetal",
                "Quality": "Standard",
                "Thickness": "0.1250",
                "*AWJFixedSpeed*": "",
                "*AWJAutomatic*": "False",
            },
        ],
    )

    rows = parse_csv_rows(csv_path)

    assert rows == []


def test_parse_csv_rows_skips_zero_or_negative_feed_rate(tmp_path):
    csv_path = tmp_path / "materials.csv"
    _write_csv(
        csv_path,
        [
            {
                "MachineType": "0",
                "Name": "Acetal",
                "Quality": "Standard",
                "Thickness": "0.1250",
                "*AWJFixedSpeed*": "0",
                "*AWJAutomatic*": "False",
            },
        ],
    )

    rows = parse_csv_rows(csv_path)

    assert rows == []
