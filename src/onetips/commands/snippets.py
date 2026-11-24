from __future__ import annotations

from pathlib import Path

from onetips.adapters.runner import run_snippets
from onetips.commands.project import load_project
from onetips.commands.result import CommandResult
from onetips.core.config import path_slug
from onetips.core.diagnostic import has_errors
from onetips.core.errors import UsageError


def run(root: Path, tip_id: str | None) -> CommandResult:
    project = load_project(root)
    if not project.ready:
        return CommandResult(project.diagnostics)
    tips = project.tips
    diagnostics = list(project.diagnostics)
    if tip_id is not None:
        path_slug(tip_id, "id")
        expected_path = project.skill / "references" / f"{tip_id}.md"
        if not expected_path.is_file():
            raise UsageError(f"unknown Tip {tip_id!r}")
        tips = [tip for tip in tips if tip.path == expected_path]
        diagnostics = [item for item in diagnostics if item.path == expected_path]
    if not has_errors(diagnostics):
        diagnostics.extend(run_snippets(root, project.config, tips))
    return CommandResult(diagnostics)
