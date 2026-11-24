from __future__ import annotations

import re
from dataclasses import dataclass, field

from onetips.core.errors import UsageError
from onetips.core.section import SECTION_KEYS

_KEBAB = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{prefix}{n}" for prefix in ("com", "lpt") for n in range(1, 10)}
_DEFAULT_TITLES = ("When to Use", "Recommended Approach", "Pitfalls", "Checklist")


@dataclass(frozen=True)
class SnippetRunner:
    ext: str
    compile: str | None
    test: str | None
    timeout: int


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    domain: str
    subjects: dict[str, str]
    categories: dict[str, str]
    sections: dict[str, str]
    snippets: dict[str, SnippetRunner] = field(default_factory=dict)


def slug(value: object, field: str) -> str:
    if not isinstance(value, str) or not _KEBAB.fullmatch(value):
        raise UsageError(f"{field} must be a lowercase kebab-case identifier")
    return value


def path_slug(value: object, field: str) -> str:
    identifier = slug(value, field)
    if len(identifier) > 64 or identifier in _RESERVED:
        raise UsageError(f"{field} must be a portable identifier of at most 64 characters: {identifier!r}")
    return identifier


def _line(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or value.splitlines() != [value]:
        raise UsageError(f"{field} must be a nonempty single-line string without outer whitespace")
    return value


def default_config(name: str) -> ProjectConfig:
    name = path_slug(name, "name")
    return ProjectConfig(name, name, {}, {"general": "General"}, dict(zip(SECTION_KEYS, _DEFAULT_TITLES, strict=True)))


def config_data(config: ProjectConfig) -> dict[str, object]:
    data: dict[str, object] = {
        "format": 1,
        "name": config.name,
        "domain": config.domain,
        "subjects": config.subjects,
        "categories": [{"id": key, "title": title} for key, title in config.categories.items()],
        "sections": config.sections,
    }
    if config.snippets:
        data["snippets"] = {
            language: {
                key: value
                for key, value in (
                    ("ext", runner.ext),
                    ("compile", runner.compile),
                    ("test", runner.test),
                    ("timeout", runner.timeout),
                )
                if value is not None
            }
            for language, runner in config.snippets.items()
        }
    return data


def _parse_snippets(data: object) -> dict[str, SnippetRunner]:
    if not isinstance(data, dict):
        raise UsageError("snippets must be a mapping")
    snippets: dict[str, SnippetRunner] = {}
    for language, entry in data.items():
        if not isinstance(language, str) or not re.fullmatch(r"\S+", language):
            raise UsageError("snippet language must be a nonempty single token")
        if not isinstance(entry, dict):
            raise UsageError(f"snippets.{language} must be a mapping")
        ext = entry.get("ext")
        if not isinstance(ext, str) or not re.fullmatch(r"[a-zA-Z0-9]+", ext):
            raise UsageError(f"snippets.{language}.ext must be ASCII alphanumeric")
        commands: dict[str, str] = {}
        for key in ("compile", "test"):
            if key in entry:
                command = entry[key]
                if not isinstance(command, str) or not command.strip():
                    raise UsageError(f"snippets.{language}.{key} must be a nonempty string")
                commands[key] = command
        timeout = entry.get("timeout", 120)
        if type(timeout) is not int or timeout <= 0:
            raise UsageError(f"snippets.{language}.timeout must be a positive integer")
        snippets[language] = SnippetRunner(ext, commands.get("compile"), commands.get("test"), timeout)
    return snippets


def _parse_subjects(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        raise UsageError("subjects must be a mapping")
    subjects: dict[str, str] = {}
    for subject, display in data.items():
        key = slug(subject, "subjects key")
        subjects[key] = _line(display, f"subjects.{key}")
    return subjects


def _parse_categories(data: object) -> dict[str, str]:
    if not isinstance(data, list) or not data:
        raise UsageError("categories must be a nonempty list")
    categories: dict[str, str] = {}
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise UsageError(f"categories[{i}] must be a mapping")
        key = slug(entry.get("id"), f"categories[{i}].id")
        if key in categories:
            raise UsageError(f"categories contains duplicate id {key!r}")
        categories[key] = _line(entry.get("title"), f"categories[{i}].title")
    return categories


def _parse_sections(data: object) -> dict[str, str]:
    if not isinstance(data, dict) or data.keys() != set(SECTION_KEYS):
        raise UsageError(f"sections must contain exactly: {', '.join(SECTION_KEYS)}")
    sections = {key: _line(data[key], f"sections.{key}") for key in SECTION_KEYS}
    if len(set(sections.values())) != len(sections):
        raise UsageError("sections must have distinct titles")
    for key, title in sections.items():
        if title.startswith("#") or title.endswith("#"):
            raise UsageError(f"sections.{key} must not begin or end with #")
    return sections


def parse_config(data: object) -> ProjectConfig:
    """Validate parsed YAML; checks run in file order so the first problem reported is the earliest field."""
    if not isinstance(data, dict):
        raise UsageError("expected a YAML mapping")
    fmt = data.get("format")
    if type(fmt) is not int or fmt != 1:
        raise UsageError("format must be the integer 1")
    name = path_slug(data.get("name"), "name")
    domain = _line(data.get("domain"), "domain")
    subjects = _parse_subjects(data.get("subjects"))
    categories = _parse_categories(data.get("categories"))
    sections = _parse_sections(data.get("sections"))
    return ProjectConfig(name, domain, subjects, categories, sections, _parse_snippets(data.get("snippets", {})))
