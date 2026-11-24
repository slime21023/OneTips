from __future__ import annotations

from pathlib import Path

from onetips.adapters.fs import is_link
from onetips.adapters.markdown import read_document
from onetips.commands._query import load_catalog, to_json
from onetips.core.errors import DataError
from onetips.core.index import IndexRow
from onetips.core.rules.metadata import validate_metadata
from onetips.core.section import select_fences, select_section
from onetips.core.snippet import Fence
from onetips.core.tip import Document


def _tip_document(skill: Path, row: IndexRow) -> Document:
    path = skill / row.path
    try:
        root = skill.resolve(strict=True)
        references = root / "references"
        candidate = root / row.path
        if is_link(references) or not references.is_dir():
            raise DataError(f"{references}: expected a plain references directory")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(references) or resolved.name != f"{row.id}.md":
            raise DataError(f"{path}: expected the indexed Tip inside references/")
        if not resolved.is_file():
            raise DataError(f"{path}: expected a regular Tip file")
        return read_document(resolved)
    except (OSError, RuntimeError, UnicodeError) as exc:
        raise DataError(f"{path}: {exc}") from exc


def _metadata(document: Document, as_json: bool) -> str:
    metadata, diagnostics = validate_metadata(document)
    if diagnostics:
        raise DataError("\n".join(f"{d.path}:{d.line}: {d.code} {d.message}" for d in diagnostics))
    if metadata is None or document.front_matter is None:
        raise DataError(f"{document.path}: missing Tip metadata")
    if not as_json:
        return document.front_matter
    fields: dict[str, object] = {
        "id": metadata.id,
        "summary": metadata.summary,
        "category": metadata.category,
        "tags": metadata.tags,
    }
    if metadata.related is not None:
        fields["related"] = metadata.related
    fields["applies_to"] = metadata.applies_to
    return to_json(fields)


def _render_fences(document: Document, fences: list[Fence], as_json: bool) -> str:
    if as_json:
        return to_json(
            [{"language": fence.snippet.language, "status": fence.snippet.status, "code": fence.snippet.code} for fence in fences]
        )
    parts: list[str] = []
    for fence in fences:
        if parts:
            parts.append("\n" if parts[-1].endswith("\n") else "\n\n")
        parts.append("".join(document.lines[fence.start : fence.end]))
    return "".join(parts)


def show(
    skill: Path,
    tip_id: str,
    *,
    metadata: bool,
    section: str | None,
    code: bool,
    lang: str | None,
    status: str | None,
    as_json: bool,
) -> str:
    catalog = load_catalog(skill)
    row = next((row for row in catalog.rows if row.id == tip_id), None)
    if row is None:
        raise DataError(f"{skill / 'INDEX.md'}: no indexed Tip {tip_id!r}")
    document = _tip_document(skill, row)
    if metadata:
        return _metadata(document, as_json)

    bounds = None
    if section is not None:
        title = catalog.sections[section]
        bounds = select_section(document.headings, title, len(document.lines))
        if bounds is None:
            raise DataError(f"{document.path}: expected exactly one top-level H2 titled {title!r}")
    if not code:
        if bounds is None:
            raise DataError("show requires a selection mode")
        return "".join(document.lines[bounds[0] : bounds[1]])

    region = document.fences if bounds is None else select_fences(document.fences, bounds, None, None)
    for fence in region:
        if not fence.snippet.language:
            raise DataError(f"{document.path}:{fence.start + 1}: E-CODE-LANG fenced code block requires a language")
        if not fence.valid_status:
            raise DataError(f"{document.path}:{fence.start + 1}: E-CODE-STATUS invalid fence status")
    selected = region if lang is None and status is None else select_fences(region, None, lang, status)
    return _render_fences(document, selected, as_json)
