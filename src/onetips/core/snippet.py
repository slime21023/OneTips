from __future__ import annotations

from dataclasses import dataclass
from typing import Final

SNIPPET_STATUSES: Final = ("unverified", "compiled", "tested")


@dataclass(frozen=True)
class Snippet:
    """One fenced code block; field names match the `show --code --json` contract."""

    language: str
    status: str
    code: str


@dataclass(frozen=True)
class Fence:
    start: int
    end: int
    snippet: Snippet
    valid_status: bool
