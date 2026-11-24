from __future__ import annotations

import json
from pathlib import Path

from onetips.adapters.index_file import read_catalog
from onetips.core.errors import DataError
from onetips.core.index import Catalog, CatalogError


def load_catalog(skill: Path) -> Catalog:
    try:
        return read_catalog(skill)
    except CatalogError as exc:
        raise DataError(f"{skill / 'INDEX.md'}:{exc.line}: E-INDEX-FORMAT {exc}") from exc
    except (OSError, UnicodeError) as exc:
        raise DataError(f"{skill / 'INDEX.md'}: {exc}") from exc


def to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False) + "\n"
