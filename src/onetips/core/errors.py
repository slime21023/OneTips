from __future__ import annotations

from pathlib import Path


class UsageError(ValueError):
    """A command or project input cannot be used (exit code 2)."""


class ConfigError(UsageError):
    """`onetips.yaml` is missing or invalid."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(message)
        self.path = path


class DataError(ValueError):
    """Required skill data is missing, invalid, or unsafe to read (exit code 1)."""
