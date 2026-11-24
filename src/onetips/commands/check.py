from __future__ import annotations

from pathlib import Path

from onetips.adapters.fs import is_link
from onetips.adapters.links import validate_readme, validate_skill
from onetips.commands.index import freshness
from onetips.commands.project import load_project
from onetips.commands.result import CommandResult
from onetips.core.diagnostic import Diagnostic, has_errors


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
        found, _ = freshness(project, write=False, diff=False)
        diagnostics.extend(found)
    return CommandResult(diagnostics)
