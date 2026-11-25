from __future__ import annotations

from pathlib import Path

from onetips.adapters.fs import is_link
from onetips.adapters.index_file import read_index_bytes, write_index_if_changed
from onetips.commands.project import load_project
from onetips.commands.result import CommandResult
from onetips.core.diagnostic import Diagnostic, has_errors
from onetips.core.index import index_diff, render_index


def _check_freshness(index_path: Path, expected: bytes) -> tuple[list[Diagnostic], str]:
    if is_link(index_path):
        return [], ""
    try:
        actual = read_index_bytes(index_path)
    except OSError as exc:
        return [Diagnostic(index_path, 1, "E-READ", str(exc))], ""
    if actual == expected:
        return [], ""
    diagnostic = Diagnostic(index_path, 1, "E-INDEX-STALE", "regenerate with onetips index")
    return [diagnostic], index_diff(actual, expected, str(index_path))


def _update_index(index_path: Path, expected: bytes) -> list[Diagnostic]:
    try:
        write_index_if_changed(index_path, expected)
    except OSError as exc:
        return [Diagnostic(index_path, 1, "E-READ", str(exc))]
    return []


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
        expected = render_index(project.config, project.tips).encode("utf-8")
        if check:
            found, output = _check_freshness(index_path, expected)
            diagnostics.extend(found)
        else:
            diagnostics.extend(_update_index(index_path, expected))
    return CommandResult(diagnostics, output)
