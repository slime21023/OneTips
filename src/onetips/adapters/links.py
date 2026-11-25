from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from onetips.adapters.fs import is_link, is_plain_dir
from onetips.adapters.hashing import is_excluded
from onetips.adapters.index_file import read_catalog
from onetips.adapters.markdown import read_document
from onetips.core.diagnostic import Diagnostic
from onetips.core.index import Catalog, CatalogError
from onetips.core.rules.anchors import heading_anchors
from onetips.core.rules.links import classify_link, leaves_scope
from onetips.core.rules.skill import compare_index, validate_skill_document
from onetips.core.tip import Document, Link


class _Links:
    def __init__(self, root: Path, documents: dict[Path, Document] | None = None, *, installed: bool = True) -> None:
        self.root = root
        self.documents = {} if documents is None else dict(documents)
        self.anchors: dict[Path, set[str]] = {}
        self.installed = installed
        self.diagnostics: list[Diagnostic] = []

    def load(self, path: Path) -> Document | None:
        if path not in self.documents:
            try:
                resolved = path.resolve()
                if not resolved.is_relative_to(self.root):
                    self.diagnostics.append(Diagnostic(path, 1, "E-LINK-ESCAPES-SKILL", "file escapes its scope"))
                    return None
                if not path.is_file():
                    raise FileNotFoundError(f"file not found: {path.name}")
                self.documents[path] = read_document(path)
            except (OSError, UnicodeError, RuntimeError) as exc:
                self.diagnostics.append(Diagnostic(path, 1, "E-READ", str(exc)))
                return None
        return self.documents[path]

    def _anchor_set(self, path: Path) -> set[str]:
        if path not in self.anchors:
            document = self.load(path)
            self.anchors[path] = set() if document is None else heading_anchors(document)
        return self.anchors[path]

    def _check_link(self, document: Document, link: Link) -> Path | None:
        dest = link.destination
        try:
            info = classify_link(dest)
            if info is None:
                return None
            escaped = info.escapes
            raw = document.path.parent / info.path if info.path else document.path
            if not escaped:
                # Check lexical and resolved paths, even if the target is missing.
                escaped = leaves_scope(raw.relative_to(self.root).parts)
            target = raw.resolve() if not escaped else raw
            if escaped or not target.is_relative_to(self.root):
                self.diagnostics.append(
                    Diagnostic(document.path, link.line, "E-LINK-ESCAPES-SKILL", f"link leaves its scope: {dest}"),
                )
                return None
            unavailable = self.installed and (
                is_excluded(target.relative_to(self.root)) or is_excluded(raw.relative_to(self.root))
            )
            if unavailable or not target.is_file():
                self.diagnostics.append(
                    Diagnostic(document.path, link.line, "E-LINK-BROKEN", f"missing installed file: {dest}"),
                )
                return None
            if info.fragment and target.suffix.lower() == ".md" and info.fragment not in self._anchor_set(target):
                self.diagnostics.append(Diagnostic(document.path, link.line, "E-LINK-ANCHOR", f"unknown anchor: {dest}"))
        except (OSError, RuntimeError, ValueError) as exc:
            self.diagnostics.append(Diagnostic(document.path, link.line, "E-LINK-BROKEN", f"{dest}: {exc}"))
            return None
        else:
            return target

    def check(self, document: Document) -> set[Path]:
        return {target for link in document.links if (target := self._check_link(document, link)) is not None}


def validate_readme(root: Path, skill: Path) -> list[Diagnostic]:
    root = root.resolve()
    links = _Links(root, installed=False)
    path = root / "README.md"
    document = links.load(path)
    if document is not None:
        targets = links.check(document)
        index = skill / "INDEX.md"
        if index.resolve() not in targets and not any(
            unquote(link.destination.split("#", 1)[0]) == index.relative_to(root).as_posix() for link in document.links
        ):
            links.diagnostics.append(Diagnostic(path, 1, "E-README-NO-INDEX-LINK", "README.md must link to its skill index"))
    return links.diagnostics


def _check_skill_file(links: _Links, root: Path) -> None:
    skill = root / "SKILL.md"
    document = links.load(skill)
    if document is None:
        return
    links.diagnostics.extend(validate_skill_document(document, root.name))
    linked = links.check(document)
    if (root / "INDEX.md").resolve() not in linked and not any(link.destination == "INDEX.md" for link in document.links):
        links.diagnostics.append(Diagnostic(skill, 1, "E-SKILL-NO-INDEX-LINK", "SKILL.md must link to INDEX.md"))


def _load_catalog(root: Path, catalog: Catalog | None, diagnostics: list[Diagnostic]) -> Catalog | None:
    """Use the supplied catalog, or parse INDEX.md; a symbolic-link index is rejected."""
    index = root / "INDEX.md"
    if is_link(index):
        diagnostics.append(Diagnostic(index, 1, "E-INDEX-FORMAT", "index must not be a symbolic link"))
        return catalog
    if catalog is not None:
        return catalog
    try:
        return read_catalog(root)
    except CatalogError as exc:
        diagnostics.append(Diagnostic(index, exc.line, "E-INDEX-FORMAT", str(exc)))
    except (OSError, UnicodeError) as exc:
        diagnostics.append(Diagnostic(index, 1, "E-INDEX-FORMAT", str(exc)))
    return None


def _check_references(links: _Links, root: Path, catalog: Catalog | None) -> None:
    references = root / "references"
    if (is_link(references) or references.exists()) and not is_plain_dir(references):
        links.diagnostics.append(Diagnostic(references, 1, "E-READ", "expected a plain references directory"))
        return
    actual = set(references.glob("*.md")) if references.is_dir() else set()
    if catalog is not None:
        links.diagnostics.extend(compare_index(catalog, root / "INDEX.md", root, actual))
    for path in sorted(actual):
        if is_link(path):
            links.diagnostics.append(Diagnostic(path, 1, "E-READ", "Tip must be a plain file"))
            continue
        tip = links.load(path)
        if tip is not None:
            links.check(tip)


def validate_skill(root: Path, catalog: Catalog | None = None, documents: dict[Path, Document] | None = None) -> list[Diagnostic]:
    root = root.resolve()
    links = _Links(root, documents)
    index = root / "INDEX.md"
    _check_skill_file(links, root)
    catalog = _load_catalog(root, catalog, links.diagnostics)
    if not is_link(index) and index.is_file():
        index_document = links.load(index)
        if index_document is not None:
            links.check(index_document)
    _check_references(links, root, catalog)
    return links.diagnostics
