"""File source boundary.

Today the DXF comes from a local file path. Later this will be replaced by
a connection to an upstream pipeline (e.g. iGEMS). Nothing downstream of
load_dxf() should know or care where the file came from -- it only ever
sees an already-loaded ezdxf.Drawing.
"""
import ezdxf
from ezdxf.document import Drawing


def load_dxf(source: str) -> Drawing:
    """Load a DXF file from a local path and return its ezdxf Drawing.

    Raises FileNotFoundError if the path does not exist, and
    ezdxf.DXFStructureError if the file is not a valid DXF.
    """
    return ezdxf.readfile(source)
