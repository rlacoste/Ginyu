import ezdxf
import pytest

from waterjet_quoter.ingestion import load_dxf


def test_load_dxf_returns_drawing_with_expected_entity(tmp_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (1, 1))
    dxf_path = tmp_path / "sample.dxf"
    doc.saveas(dxf_path)

    drawing = load_dxf(str(dxf_path))

    entities = list(drawing.modelspace())
    assert len(entities) == 1
    assert entities[0].dxftype() == "LINE"


def test_load_dxf_raises_for_missing_file():
    with pytest.raises(FileNotFoundError):
        load_dxf("/nonexistent/path/does_not_exist.dxf")
