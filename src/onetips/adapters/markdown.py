from __future__ import annotations

import re
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token
from yaml import YAMLError

from onetips.adapters.yamlio import load_yaml
from onetips.core.snippet import SNIPPET_STATUSES, Fence, Snippet
from onetips.core.tip import Document, Heading, Link


class _SourceParser(MarkdownIt):
    def validateLink(self, url: str) -> bool:  # noqa: N802 - overrides markdown-it's camelCase hook
        # Inspect even destinations the renderer would reject; we never render or fetch them.
        return True


_MARKDOWN = _SourceParser("commonmark").enable("table")
_TASK = re.compile(r"^\[[ xX]\]\s+\S")


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.names: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.names.update(value for key, value in attrs if key in {"id", "name"} and value)


def _plain_text(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.type in {"text", "code_inline"}:
            parts.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
        elif token.type == "image" and token.children:
            parts.append(_plain_text(token.children))
    return "".join(parts)


def _collect_inline(tokens: list[Token], line: int, links: list[Link], anchors: _Anchors) -> None:
    for token in tokens:
        if token.type in {"link_open", "image"}:
            target = token.attrGet("href" if token.type == "link_open" else "src")
            if isinstance(target, str):
                links.append(Link(line, target))
        if token.type == "html_inline":
            anchors.feed(token.content)
        if token.children:
            _collect_inline(token.children, line, links, anchors)


def _front_matter(lines: list[str]) -> tuple[str | None, object, str | None, int]:
    if not lines or lines[0].rstrip("\n") != "---":
        return None, None, None, 0
    for end in range(1, len(lines)):
        if lines[end].rstrip("\n") == "---":
            raw = "".join(lines[1:end])
            try:
                return raw, load_yaml(raw), None, end + 1
            except (YAMLError, ValueError, OverflowError, RecursionError) as exc:
                return raw, None, str(exc), end + 1
    return None, None, "unclosed front matter", len(lines)


def _fence(token: Token, start: int, end: int) -> Fence:
    words = token.info.split()
    language = words[0] if words and not words[0].startswith("status=") else ""
    statuses = [word.removeprefix("status=") for word in words if word.startswith("status=")]
    status = statuses[0] if statuses else "unverified"
    return Fence(start, end, Snippet(language, status, token.content), len(statuses) <= 1 and status in SNIPPET_STATUSES)


class _Collector:
    """Walk markdown-it tokens once and gather headings, fences, links, anchors and checklist items."""

    def __init__(self, tokens: list[Token], body_start: int) -> None:
        self.tokens = tokens
        self.body_start = body_start
        self.headings: list[Heading] = []
        self.fences: list[Fence] = []
        self.links: list[Link] = []
        self.anchors = _Anchors()
        self.checklist_items: list[int] = []
        self._handlers: dict[str, Callable[[int, Token, int, int], None]] = {
            "heading_open": self._on_heading,
            "fence": self._on_fence,
            "inline": self._on_inline,
            "html_block": self._on_html,
            "list_item_open": self._on_list_item,
        }

    def collect(self) -> None:
        # Tokens without a `map` (closing tags, inline children) inherit the previous token's span.
        start = end = self.body_start
        for index, token in enumerate(self.tokens):
            if token.map is not None:
                start, end = token.map[0] + self.body_start, token.map[1] + self.body_start
            handler = self._handlers.get(token.type)
            if handler is not None:
                handler(index, token, start, end)
        self.anchors.close()

    def _on_heading(self, index: int, token: Token, start: int, end: int) -> None:
        inline = self.tokens[index + 1]
        display = _plain_text(inline.children or [])
        self.headings.append(Heading(inline.content, display, int(token.tag[1:]), token.level == 0, start))

    def _on_fence(self, index: int, token: Token, start: int, end: int) -> None:
        self.fences.append(_fence(token, start, end))

    def _on_inline(self, index: int, token: Token, start: int, end: int) -> None:
        _collect_inline(token.children or [], start + 1, self.links, self.anchors)

    def _on_html(self, index: int, token: Token, start: int, end: int) -> None:
        self.anchors.feed(token.content)

    def _on_list_item(self, index: int, token: Token, start: int, end: int) -> None:
        if self.tokens[index + 1].type == "paragraph_open" and _TASK.match(self.tokens[index + 2].content):
            self.checklist_items.append(start)


def read_document(path: Path) -> Document:
    # splitlines() also treats Unicode separators as physical lines; CommonMark does not.
    text = path.read_text(encoding="utf-8")
    lines = [match.group() for match in re.finditer(r"[^\n]*\n|[^\n]+$", text)]
    raw, metadata, front_error, body_start = _front_matter(lines)
    collector = _Collector(_MARKDOWN.parse("".join(lines[body_start:])), body_start)
    collector.collect()
    return Document(
        path,
        lines,
        raw,
        metadata,
        front_error,
        body_start,
        collector.headings,
        collector.fences,
        collector.links,
        collector.anchors.names,
        collector.checklist_items,
    )
