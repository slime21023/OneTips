from __future__ import annotations

import tempfile
from pathlib import Path


def is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def is_plain_dir(path: Path) -> bool:
    return not is_link(path) and path.is_dir()


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
