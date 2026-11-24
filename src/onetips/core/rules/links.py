from __future__ import annotations

from dataclasses import dataclass
from pathlib import PureWindowsPath
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class LinkTarget:
    path: str
    fragment: str
    escapes: bool


def classify_link(destination: str) -> LinkTarget | None:
    """Lexically classify a link; `None` means a remote link that is never checked."""
    parsed = urlsplit(destination)
    decoded = unquote(parsed.path)
    escaped = (bool(PureWindowsPath(destination).drive) and not destination.startswith("//")) or parsed.scheme == "file"
    if not escaped and (parsed.scheme or parsed.netloc or destination.startswith("//")):
        return None
    escaped = escaped or decoded.startswith("/") or "\\" in decoded
    return LinkTarget(decoded, unquote(parsed.fragment), escaped)


def leaves_scope(parts: tuple[str, ...]) -> bool:
    """True when a relative path climbs above its starting directory."""
    depth = 0
    for part in parts:
        depth += -1 if part == ".." else 1
        if depth < 0:
            return True
    return False
