from __future__ import annotations

from onetips.core.config import ProjectConfig
from onetips.core.diagnostic import Diagnostic
from onetips.core.section import SECTION_KEYS
from onetips.core.tip import Document, Heading

Diagnostics = list[Diagnostic]


def _diagnostic(document: Document, line: int, code: str, message: str) -> Diagnostic:
    return Diagnostic(document.path, line, code, message)


def _check_title(document: Document) -> tuple[str, Diagnostics]:
    """The title is the text of the single top-level H1, which must be the first block."""
    first = next((i for i in range(document.body_start, len(document.lines)) if document.lines[i].strip()), None)
    h1s = [heading for heading in document.headings if heading.level == 1]
    if len(h1s) == 1 and h1s[0].top_level and h1s[0].start == first and h1s[0].display.strip():
        return h1s[0].display.strip(), []
    line = h1s[1].start if len(h1s) > 1 else first
    message = "expected a single nonempty top-level H1 as the first block"
    return "", [_diagnostic(document, line + 1 if line is not None else 1, "E-H1", message)]


def _check_checklist(document: Document, h2s: list[Heading], start: int) -> Diagnostics:
    end = next((heading.start for heading in h2s if heading.start > start), len(document.lines))
    if any(start < item < end for item in document.checklist_items):
        return []
    return [_diagnostic(document, start + 1, "E-CHECKLIST-EMPTY", "checklist must contain a nonempty task list item")]


def _check_sections(document: Document, config: ProjectConfig) -> Diagnostics:
    """Each configured H2 must appear once, in the configured order; the checklist needs an item."""
    diagnostics: Diagnostics = []
    h2s = [heading for heading in document.headings if heading.level == 2 and heading.top_level]
    by_title: dict[str, list[Heading]] = {name: [] for name in config.sections.values()}
    for heading in h2s:
        if heading.text in by_title:
            by_title[heading.text].append(heading)
    previous = -1
    for key in SECTION_KEYS:
        name = config.sections[key]
        matches = by_title[name]
        if not matches:
            diagnostics.append(_diagnostic(document, 1, "E-SECTION-MISSING", f"missing section {name!r}"))
            continue
        for duplicate in matches[1:]:
            diagnostics.append(_diagnostic(document, duplicate.start + 1, "E-SECTION-DUPLICATE", f"duplicate section {name!r}"))
        start = matches[0].start
        if start < previous:
            diagnostics.append(_diagnostic(document, start + 1, "E-SECTION-ORDER", f"section {name!r} is out of order"))
        previous = max(start, previous)
        if key == "checklist":
            diagnostics.extend(_check_checklist(document, h2s, start))
    return diagnostics


def _check_fences(document: Document) -> Diagnostics:
    diagnostics: Diagnostics = []
    for fence in document.fences:
        line = fence.start + 1
        code = fence.snippet.code
        if not fence.snippet.language:
            diagnostics.append(_diagnostic(document, line, "E-CODE-LANG", "fenced code block requires a language"))
        if not fence.valid_status:
            message = "expected at most one status=unverified, status=compiled or status=tested"
            diagnostics.append(_diagnostic(document, line, "E-CODE-STATUS", message))
        if code.count("\n") + bool(code and not code.endswith("\n")) > 60:
            diagnostics.append(_diagnostic(document, line, "W-SNIPPET-LONG", "fenced code block exceeds 60 lines"))
    return diagnostics


def validate_body(document: Document, config: ProjectConfig) -> tuple[str, Diagnostics]:
    title, diagnostics = _check_title(document)
    diagnostics.extend(_check_sections(document, config))
    diagnostics.extend(_check_fences(document))
    return title, diagnostics
