from __future__ import annotations

from dataclasses import dataclass

from onetips.core.diagnostic import Diagnostic


@dataclass(frozen=True)
class CommandResult:
    diagnostics: list[Diagnostic]
    output: str = ""
