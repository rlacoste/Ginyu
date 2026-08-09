import pytest

from waterjet_quoter.db import _resolve_database_url
from waterjet_quoter.material_prices import load_price_table
from waterjet_quoter.set_material_price import build_arg_parser, main, set_price


def test_arg_parser_requires_material_and_price():
    parser = build_arg_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--material", "Copper"])  # missing --price-per-lb


def test_arg_parser_defaults_machine_rate_multiplier_to_one():
    parser = build_arg_parser()

    args = parser.parse_args(["--material", "Aluminium", "--price-per-lb", "1.85"])

    assert args.material == "Aluminium"
    assert args.price_per_lb == 1.85
    assert args.machine_rate_multiplier == 1.0


@pytest.mark.skipif(
    not _resolve_database_url(),
    reason="DATABASE_URL not configured -- requires a live Supabase connection",
)
def test_set_price_upserts_into_real_database():
    set_price("Test Material XYZ", 9.99, 1.5)

    table = load_price_table()

    assert table["Test Material XYZ"]["price_per_lb"] == 9.99
    assert table["Test Material XYZ"]["machine_rate_multiplier"] == 1.5

    # Upsert again with a different price -- must update, not duplicate.
    set_price("Test Material XYZ", 12.34, 1.0)
    table = load_price_table()
    assert table["Test Material XYZ"]["price_per_lb"] == 12.34
    assert table["Test Material XYZ"]["machine_rate_multiplier"] == 1.0


@pytest.mark.skipif(
    not _resolve_database_url(),
    reason="DATABASE_URL not configured -- requires a live Supabase connection",
)
def test_main_cli_sets_price(capsys):
    exit_code = main(
        ["--material", "Test Material ABC", "--price-per-lb", "2.50", "--machine-rate-multiplier", "2.0"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Test Material ABC" in captured.out

    table = load_price_table()
    assert table["Test Material ABC"]["price_per_lb"] == 2.50
