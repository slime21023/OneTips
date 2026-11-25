from __future__ import annotations

import tempfile
from pathlib import Path

from onetips.core.errors import UsageError


def is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def is_plain_dir(path: Path) -> bool:
    return not is_link(path) and path.is_dir()


def is_occupied(path: Path) -> bool:
    return is_link(path) or path.exists()


def _mkdir_parents(path: Path, created: list[Path]) -> None:
    if is_plain_dir(path):
        return
    _mkdir_parents(path.parent, created)
    path.mkdir()
    created.append(path)


def _write_exclusive(path: Path, text: str, created: list[Path]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as file:
        created.append(path)
        file.write(text)


def _rollback(files: list[Path], dirs: list[Path], error: OSError) -> UsageError:
    failures: list[str] = []
    for path in reversed(files):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            failures.append(str(exc))
    for path in reversed(dirs):
        try:
            path.rmdir()
        except OSError as exc:
            failures.append(str(exc))
    detail = f"; cleanup failed: {'; '.join(failures)}" if failures else ""
    return UsageError(f"{error}{detail}")


def create_files(contents: dict[Path, str], *, mkdir: Path | None = None) -> None:
    """Create directories (if requested) and write new UTF-8 LF files exclusively, rolling back on failure."""
    files: list[Path] = []
    dirs: list[Path] = []
    try:
        if mkdir is not None:
            _mkdir_parents(mkdir, dirs)
        for path, text in contents.items():
            _write_exclusive(path, text, files)
    except OSError as exc:
        raise _rollback(files, dirs, exc) from exc


def atomic_write(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".INDEX-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.close()
            temporary.replace(path)
        finally:
            handle.close()
            temporary.unlink(missing_ok=True)
