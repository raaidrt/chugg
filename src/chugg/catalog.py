"""The bundled, immutable catalog, shared by native and browser Python."""

import json
from pathlib import Path
from typing import cast

from chugg.models import Catalog

catalog = cast(Catalog, json.loads((Path(__file__).parent / "data/catalog.json").read_text()))
openings = catalog["openings"]
metadata = catalog["metadata"]
