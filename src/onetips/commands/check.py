from __future__ import annotations

from pathlib import Path

from onetips.adapters.fs import is_link
from onetips.adapters.index_file import read_index_bytes
from onetips.adapters.links import validate_readme, validate_skill
from onetips.commands.project import Project, load_project
from onetips.commands.result import CommandResult
from onetips.core.diagnostic import Diagnostic, has_errors
from onetips.core.index import render_index


def _check_index_freshness(project: Project) -> list[Diagnostic]:
    index_path = project.skill / "INDEX.md"
    if is_link(index_path):
        return []
    expected = render_index(project.config, project.tips).encode("utf-8")
    try:
        actual = read_index_bytes(index_path)
    except OSError as exc:
        return [Diagnostic(index_path, 1, "E-READ", str(exc))]
    if actual != expected:
        return [Diagnostic(index_path, 1, "E-INDEX-STALE", "regenerate with onetips index")]
    return []


def run(root: Path) -> CommandResult:
    project = load_project(root)
    if not project.ready:
        return CommandResult(project.diagnostics)
    diagnostics = list(project.diagnostics)
    tips_valid = not has_errors(diagnostics)
    index_path = project.skill / "INDEX.md"
    documents = {tip.path: tip.document for tip in project.tips}
    diagnostics.extend(validate_readme(root, project.skill))
    if not is_link(index_path):
        diagnostics.extend(validate_skill(project.skill, documents=documents))
    else:
        diagnostics.append(Diagnostic(index_path, 1, "E-INDEX-FORMAT", "index must not be a symbolic link"))
    if tips_valid:
        diagnostics.extend(_check_index_freshness(project))
    return CommandResult(diagnostics)
