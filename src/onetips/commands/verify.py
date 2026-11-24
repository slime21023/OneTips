from __future__ import annotations

from pathlib import Path

from onetips.adapters.hashing import computed_hash
from onetips.adapters.links import validate_skill
from onetips.commands.result import CommandResult
from onetips.core.diagnostic import Diagnostic, has_errors


def run(skill: Path) -> CommandResult:
    try:
        diagnostics = validate_skill(skill)
        output = "" if has_errors(diagnostics) else f"computedHash: {computed_hash(skill)}\n"
        return CommandResult(diagnostics, output)
    except (OSError, RuntimeError) as exc:
        return CommandResult([Diagnostic(skill, 1, "E-READ", str(exc))])
