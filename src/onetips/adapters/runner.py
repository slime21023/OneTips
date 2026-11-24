from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile

from onetips.core.config import ProjectConfig, SnippetRunner
from onetips.core.diagnostic import Diagnostic
from onetips.core.tip import Tip

_ARGUMENT = re.compile(r"(?<!\S)\{(file|dir)\}(?!\S)")


def _stop(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        # Killing only cmd.exe leaves its child alive, holding the project directory open.
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    if process.poll() is None:
        process.kill()
    process.wait()


def _execute(root: Path, source: Path, command: str, timeout: int) -> str | None:
    env = dict(os.environ, ONETIPS_SNIPPET_FILE=str(source), ONETIPS_SNIPPET_DIR=str(source.parent))

    def argument(match: re.Match[str]) -> str:
        variable = "ONETIPS_SNIPPET_" + match[1].upper()
        return f'"%{variable}%"' if os.name == "nt" else f'"${variable}"'

    expanded = _ARGUMENT.sub(argument, command)
    with TemporaryFile() as output:
        try:
            with subprocess.Popen(
                expanded,
                cwd=root,
                env=env,
                shell=True,
                start_new_session=os.name != "nt",
                stdout=output,
                stderr=subprocess.STDOUT,
            ) as process:
                try:
                    status = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    _stop(process)
                    return f"timed out after {timeout}s"
        except OSError as exc:
            return str(exc)
        if status:
            end = output.seek(0, os.SEEK_END)
            output.seek(max(0, end - 2048))
            lines = output.read(2048).decode(errors="replace").strip().splitlines()
            return f"exited {status}" + (f": {lines[-1]}" if lines else "")
    return None


def _phases(runner: SnippetRunner, status: str) -> list[tuple[str, str]] | None:
    if status == "compiled":
        return [("compile", runner.compile)] if runner.compile is not None else None
    if runner.test is None:
        return None
    steps = [("compile", runner.compile)] if runner.compile is not None else []
    return [*steps, ("test", runner.test)]


def run_snippets(root: Path, config: ProjectConfig, tips: list[Tip]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    with TemporaryDirectory(prefix="onetips snippets ") as scratch:
        for tip in tips:
            for fence in tip.document.fences:
                snippet = fence.snippet
                if snippet.status == "unverified":
                    continue
                line = fence.start + 1
                runner = config.snippets.get(snippet.language)
                phases = None if runner is None else _phases(runner, snippet.status)
                if runner is None or phases is None:
                    required = "compile" if snippet.status == "compiled" else "test"
                    diagnostics.append(
                        Diagnostic(tip.path, line, "E-SNIPPET-NO-COMMAND", f"{snippet.language} needs a {required} command")
                    )
                    continue
                path = Path(scratch).resolve() / tip.metadata.id / f"{line}.{runner.ext}"
                try:
                    path.parent.mkdir(exist_ok=True)
                    path.write_text(snippet.code, encoding="utf-8", newline="\n")
                    for phase, command in phases:
                        failure = _execute(root, path, command, runner.timeout)
                        if failure is not None:
                            diagnostics.append(Diagnostic(tip.path, line, "E-SNIPPET-FAILED", f"{phase}: {failure}"))
                            break
                except OSError as exc:
                    diagnostics.append(Diagnostic(tip.path, line, "E-SNIPPET-FAILED", str(exc)))
    return diagnostics
