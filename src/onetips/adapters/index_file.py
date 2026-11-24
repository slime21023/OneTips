from __future__ import annotations

from pathlib import Path

from onetips.core.index import Catalog, CatalogError, parse_catalog


def read_catalog(skill: Path) -> Catalog:
    path = skill / "INDEX.md"
    if path.is_symlink():
        try:
            resolved = path.resolve(strict=True)
        except RuntimeError as exc:
            raise CatalogError(1, "index symlink could not be resolved") from exc
        if not resolved.is_relative_to(skill.resolve()):
            raise CatalogError(1, "index symlink escapes the skill directory")
        path = resolved
    if not path.is_file():
        raise FileNotFoundError(f"{path}: expected a regular index file")
    return parse_catalog(path.read_text(encoding="utf-8"))
