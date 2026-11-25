from __future__ import annotations

from pathlib import Path

from onetips.adapters.fs import atomic_write, is_link
from onetips.core.index import Catalog, CatalogError, parse_catalog


def read_index_bytes(index_path: Path) -> bytes | None:
    """Return raw INDEX.md bytes, or None when absent or a symbolic link."""
    if is_link(index_path):
        return None
    try:
        return index_path.read_bytes()
    except FileNotFoundError:
        return None


def write_index_if_changed(index_path: Path, expected: bytes) -> bool:
    """Atomically write `expected` to `index_path` only when its bytes differ."""
    if read_index_bytes(index_path) == expected:
        return False
    atomic_write(index_path, expected)
    return True


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
