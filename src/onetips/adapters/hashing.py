from __future__ import annotations

import errno
import hashlib
from pathlib import Path

from onetips.adapters.fs import is_link

_SKIP_DIRS = {".git", "__pycache__", "__pypackages__"}


def is_excluded(path: Path) -> bool:
    return path.name == "metadata.json" or any(part in _SKIP_DIRS for part in path.parts)


def _link_target(path: Path, root: Path) -> Path | None:
    """Resolve a symlink or junction; None when it is broken, looping, or points outside `root`."""
    try:
        target = path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError):
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return None
        raise
    return target if target.is_relative_to(root) else None


def _collect(directory: Path, root: Path, ancestors: set[Path], files: list[tuple[bytes, Path]]) -> None:
    for path in directory.iterdir():
        target: Path | None = _link_target(path, root) if is_link(path) else path
        if target is None:
            continue
        if target.is_dir():
            if path.name not in _SKIP_DIRS and target not in ancestors:
                _collect(path, root, ancestors | {target.resolve()}, files)
        elif path.name != "metadata.json" and target.is_file():
            files.append((path.relative_to(root).as_posix().encode(), target))


def _digest(files: list[tuple[bytes, Path]]) -> str:
    """SHA-256 over `path NUL length NUL content`, with CRLF normalized in text files."""
    digest = hashlib.sha256()
    for name, path in sorted(files):
        data = path.read_bytes()
        if b"\0" not in data:
            data = data.replace(b"\r\n", b"\n")
        digest.update(name)
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


def computed_hash(root: Path) -> str:
    root = root.resolve(strict=True)
    files: list[tuple[bytes, Path]] = []
    _collect(root, root, {root}, files)
    return _digest(files)
