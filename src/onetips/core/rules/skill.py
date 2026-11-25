from __future__ import annotations

from pathlib import Path

from onetips.core.config import is_path_slug
from onetips.core.diagnostic import Diagnostic
from onetips.core.index import Catalog
from onetips.core.tip import Document


def _valid_description(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1024


def _valid_metadata(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())


def validate_skill_document(document: Document, directory_name: str) -> list[Diagnostic]:
    skill = document.path
    diagnostics: list[Diagnostic] = []
    data = document.metadata
    raw_name = data.get("name") if isinstance(data, dict) else None
    name = raw_name if is_path_slug(raw_name) else None
    if not isinstance(data, dict) or name is None or document.front_error is not None:
        message = document.front_error or "valid name and description required"
        diagnostics.append(Diagnostic(skill, 1, "E-SKILL-FRONTMATTER", message))
    else:
        if not _valid_description(data.get("description")) or not _valid_metadata(data.get("metadata", {})):
            diagnostics.append(Diagnostic(skill, 1, "E-SKILL-FRONTMATTER", "invalid description or metadata"))
        if directory_name != name:
            diagnostics.append(Diagnostic(skill, 1, "E-SKILL-NAME-MISMATCH", f"expected name {directory_name!r}, got {name!r}"))
    if len(document.lines) > 500:
        diagnostics.append(Diagnostic(skill, 1, "W-SKILL-LONG", "skill exceeds 500 lines"))
    return diagnostics


def compare_index(catalog: Catalog, index_path: Path, root: Path, actual: set[Path]) -> list[Diagnostic]:
    indexed = {root / row.path for row in catalog.rows}
    diagnostics: list[Diagnostic] = []
    for missing in sorted(indexed - actual):
        diagnostics.append(Diagnostic(index_path, 1, "E-LINK-BROKEN", f"missing indexed reference: {missing.name}"))
    for unlisted in sorted(actual - indexed):
        diagnostics.append(Diagnostic(index_path, 1, "E-INDEX-MISSING-ENTRY", f"index does not list {unlisted.name}"))
    return diagnostics
