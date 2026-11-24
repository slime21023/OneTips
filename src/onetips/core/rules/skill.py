from __future__ import annotations

import contextlib
from pathlib import Path

from onetips.core.config import path_slug
from onetips.core.diagnostic import Diagnostic
from onetips.core.errors import UsageError
from onetips.core.index import Catalog
from onetips.core.tip import Document


def validate_skill_document(document: Document, directory_name: str) -> list[Diagnostic]:
    skill = document.path
    diagnostics: list[Diagnostic] = []
    data = document.metadata
    name = None
    if isinstance(data, dict):
        with contextlib.suppress(UsageError):
            name = path_slug(data.get("name"), "name")
    if not isinstance(data, dict) or name is None or document.front_error is not None:
        message = document.front_error or "valid name and description required"
        diagnostics.append(Diagnostic(skill, 1, "E-SKILL-FRONTMATTER", message))
    else:
        desc = data.get("description")
        metadata = data.get("metadata", {})
        if (
            not isinstance(desc, str)
            or not desc.strip()
            or len(desc) > 1024
            or not isinstance(metadata, dict)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items())
        ):
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
