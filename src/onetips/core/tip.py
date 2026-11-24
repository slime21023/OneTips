from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onetips.core.snippet import Fence


@dataclass(frozen=True)
class Heading:
    text: str
    display: str
    level: int
    top_level: bool
    start: int


@dataclass(frozen=True)
class Link:
    line: int
    destination: str


@dataclass(frozen=True)
class Document:
    path: Path
    lines: list[str]
    front_matter: str | None
    metadata: Any  # parsed YAML; mypyc dataclasses cannot resolve the annotation `object`
    front_error: str | None
    body_start: int
    headings: list[Heading]
    fences: list[Fence]
    links: list[Link]
    explicit_anchors: set[str]
    checklist_items: list[int]  # Zero-based physical lines.


@dataclass(frozen=True)
class TipMetadata:
    id: str
    summary: str
    category: str
    tags: tuple[str, ...]
    related: tuple[str, ...] | None
    applies_to: dict[str, str]


@dataclass(frozen=True)
class Tip:
    path: Path
    metadata: TipMetadata
    title: str
    document: Document
