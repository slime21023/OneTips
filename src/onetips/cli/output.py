from __future__ import annotations

import sys
from io import TextIOWrapper
from pathlib import Path

from onetips.core.diagnostic import Diagnostic


def report(diagnostics: list[Diagnostic]) -> int:
    seen: set[tuple[Path, int, str, str]] = set()
    errors = warnings = 0
    for diagnostic in diagnostics:
        key = (diagnostic.path, diagnostic.line, diagnostic.code, diagnostic.message)
        if key in seen:
            continue
        seen.add(key)
        if diagnostic.code.startswith("W-"):
            warnings += 1
        else:
            errors += 1
        message = " ".join(diagnostic.message.splitlines())
        print(f"{diagnostic.path}:{diagnostic.line}: {diagnostic.code} {message}", file=sys.stderr)
    print(f"{errors} errors, {warnings} warnings", file=sys.stderr if seen else sys.stdout)
    return int(errors != 0)


def write_stdout(text: str) -> None:
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode("utf-8"))
    else:
        sys.stdout.write(text)
