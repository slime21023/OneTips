from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Diagnostic:
    path: Path
    line: int
    code: str
    message: str


def has_errors(items: list[Diagnostic]) -> bool:
    return any(not item.code.startswith("W-") for item in items)
