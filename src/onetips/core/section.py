from __future__ import annotations

from typing import Final

from onetips.core.snippet import Fence
from onetips.core.tip import Heading

SECTION_KEYS: Final = ("when", "approach", "pitfalls", "checklist")


def select_section(headings: list[Heading], title: str, line_count: int) -> tuple[int, int] | None:
    start: int | None = None
    end = line_count
    for heading in headings:
        if not heading.top_level or heading.level != 2:
            continue
        if start is not None and end == line_count:
            end = heading.start
        if heading.text == title:
            if start is not None:
                return None
            start = heading.start
    return None if start is None else (start, end)


def select_fences(
    fences: list[Fence],
    bounds: tuple[int, int] | None,
    language: str | None,
    status: str | None,
) -> list[Fence]:
    return [
        fence
        for fence in fences
        if (bounds is None or (bounds[0] <= fence.start and fence.end <= bounds[1]))
        and (language is None or fence.snippet.language == language)
        and (status is None or fence.snippet.status == status)
    ]
