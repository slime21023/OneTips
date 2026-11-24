from __future__ import annotations

from pathlib import Path
from stat import S_ISDIR, S_ISREG

from onetips.adapters.fs import is_link
from onetips.adapters.markdown import read_document
from onetips.core.diagnostic import Diagnostic
from onetips.core.tip import Document


def read_tip_documents(skill: Path) -> tuple[list[Document], list[Diagnostic]]:
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
        descend: list[Path] = []
        for child in children:
            try:
                mode = child.lstat().st_mode
                linked = is_link(child)
                if child.suffix.lower() == ".md":
                    if linked or not S_ISREG(mode) or directory != references or child.suffix != ".md":
                        diagnostics.append(Diagnostic(child, 1, "E-READ", "Tips must be direct regular .md files in references"))
                    else:
                        documents.append(read_document(child))
                if not linked and S_ISDIR(mode):
                    descend.append(child)
            except (OSError, UnicodeError) as exc:
                diagnostics.append(Diagnostic(child, 1, "E-READ", str(exc)))
        directories.extend(reversed(descend))
    return documents, diagnostics
