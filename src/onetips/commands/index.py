from __future__ import annotations

import difflib
from pathlib import Path

from onetips.adapters.fs import atomic_write, is_link
from onetips.commands.project import Project, load_project
from onetips.commands.result import CommandResult
from onetips.core.diagnostic import Diagnostic, has_errors
from onetips.core.index import render_index


def freshness(project: Project, *, write: bool, diff: bool) -> tuple[list[Diagnostic], str]:
    """Compare (or rewrite) INDEX.md against the generated index."""
    index_path = project.skill / "INDEX.md"
    diagnostics: list[Diagnostic] = []
    output = ""
    try:
        expected = render_index(project.config, project.tips).encode("utf-8")
        try:
            actual = index_path.read_bytes() if not is_link(index_path) else None
        except FileNotFoundError:
            actual = None
        if write:
            if expected != actual:
                atomic_write(index_path, expected)
        elif expected != actual and not is_link(index_path):
            diagnostics.append(Diagnostic(index_path, 1, "E-INDEX-STALE", "regenerate with onetips index"))
            if diff:
                output = "".join(
                    difflib.unified_diff(
                        (actual or b"").decode("utf-8", errors="replace").splitlines(keepends=True),
                        expected.decode("utf-8").splitlines(keepends=True),
                        fromfile=str(index_path),
                        tofile="generated INDEX.md",
                    )
                )
    except OSError as exc:
        diagnostics.append(Diagnostic(index_path, 1, "E-READ", str(exc)))
    return diagnostics, output


def run(root: Path, *, check: bool) -> CommandResult:
    project = load_project(root)
    if not project.ready:
        return CommandResult(project.diagnostics)
    diagnostics = list(project.diagnostics)
    tips_valid = not has_errors(diagnostics)
    index_path = project.skill / "INDEX.md"
    if is_link(index_path):
        diagnostics.append(Diagnostic(index_path, 1, "E-INDEX-FORMAT", "index must not be a symbolic link"))
    if has_errors(diagnostics) and not check:
        return CommandResult(diagnostics)
    output = ""
    if tips_valid:
        found, output = freshness(project, write=not check, diff=True)
        diagnostics.extend(found)
    return CommandResult(diagnostics, output)
