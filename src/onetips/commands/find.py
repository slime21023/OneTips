from __future__ import annotations

from pathlib import Path

from onetips.commands._query import load_catalog, to_json
from onetips.core.index import find_rows


def find(
    skill: Path,
    tip_id: str | None,
    category: str | None,
    tag: str | None,
    keyword: str | None,
    as_json: bool,
) -> str:
    rows = find_rows(load_catalog(skill), tip_id, category, tag, keyword)
    if as_json:
        return to_json(
            [
                {
                    "id": row.id,
                    "title": row.title,
                    "summary": row.summary,
                    "category": row.category,
                    "tags": row.tags,
                    "applies_to": row.applies_to,
                    "path": row.path,
                }
                for row in rows
            ]
        )
    return "".join(
        f"- [{row.id}]({row.path}) — {row.title} — {row.summary}" + (f" ({row.applies_to})" if row.applies_to else "") + "\n"
        for row in rows
    )
