from __future__ import annotations

from pathlib import Path
from stat import S_ISDIR, S_ISREG

from onetips.adapters.fs import is_link, is_plain_dir
from onetips.adapters.markdown import read_document
from onetips.core.diagnostic import Diagnostic
from onetips.core.errors import DataError
from onetips.core.index import IndexRow
from onetips.core.tip import Document


def _inspect_entry(
    child: Path,
    directory: Path,
    references: Path,
    documents: list[Document],
    diagnostics: list[Diagnostic],
) -> Path | None:
    """Validate one entry under `references/`; return `child` if it is a subdirectory to descend into."""
    try:
        mode = child.lstat().st_mode
        linked = is_link(child)
        if child.suffix.lower() == ".md":
            if linked or not S_ISREG(mode) or directory != references or child.suffix != ".md":
                diagnostics.append(Diagnostic(child, 1, "E-READ", "Tips must be direct regular .md files in references"))
            else:
                documents.append(read_document(child))
        if not linked and S_ISDIR(mode):
            return child
    except (OSError, UnicodeError) as exc:
        diagnostics.append(Diagnostic(child, 1, "E-READ", str(exc)))
    return None


def read_tip_documents(skill: Path) -> tuple[list[Document], list[Diagnostic]]:
    """Read direct `.md` Tips in `references/`; descend into subdirectories to report misplaced `.md` files."""
    diagnostics: list[Diagnostic] = []
    references = skill / "references"
    try:
        usable = not (is_link(skill) or is_link(references)) and S_ISDIR(references.lstat().st_mode)
    except OSError as exc:
        diagnostics.append(Diagnostic(references, 1, "E-READ", str(exc)))
        return [], diagnostics
    if not usable:
        diagnostics.append(Diagnostic(references, 1, "E-READ", "references must be a real directory in the skill"))
        return [], diagnostics

    documents: list[Document] = []
    directories = [references]
    while directories:
        directory = directories.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda child: child.name.encode("utf-8", "surrogatepass"))
        except OSError as exc:
            diagnostics.append(Diagnostic(directory, 1, "E-READ", str(exc)))
            continue
        descend = [
            subdir
            for child in children
            if (subdir := _inspect_entry(child, directory, references, documents, diagnostics)) is not None
        ]
        directories.extend(reversed(descend))
    return documents, diagnostics


def read_indexed_tip(skill: Path, row: IndexRow) -> Document:
    """Safely read one Tip referenced by `INDEX.md`, rejecting symlinks or paths escaping `references/`."""
    path = skill / row.path
    try:
        root = skill.resolve(strict=True)
        references = root / "references"
        candidate = root / row.path
        if not is_plain_dir(references):
            raise DataError(f"{references}: expected a plain references directory")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(references) or resolved.name != f"{row.id}.md":
            raise DataError(f"{path}: expected the indexed Tip inside references/")
        if not resolved.is_file():
            raise DataError(f"{path}: expected a regular Tip file")
        return read_document(resolved)
    except (OSError, RuntimeError, UnicodeError) as exc:
        raise DataError(f"{path}: {exc}") from exc
