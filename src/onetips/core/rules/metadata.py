from __future__ import annotations

from collections import Counter

from onetips.core.config import ProjectConfig, path_slug, slug
from onetips.core.diagnostic import Diagnostic
from onetips.core.errors import UsageError
from onetips.core.tip import Document, TipMetadata

Diagnostics = list[Diagnostic]

_KEYS = {"id", "summary", "category", "tags", "related", "applies_to"}


def _identifier(value: object, *, portable: bool = False, limit: int | None = None) -> str | None:
    try:
        result = (path_slug if portable else slug)(value, "ID")
    except UsageError:
        return None
    return result if limit is None or len(result) <= limit else None


def _single_line(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() and value.splitlines() == [value] else None


Problems = list[tuple[str, str]]  # (code, message) pairs; line is always 1 for front matter


def _check_frontmatter(document: Document) -> tuple[dict[object, object] | None, Problems]:
    if document.front_error is not None:
        return None, [("E-FRONTMATTER-INVALID", " ".join(document.front_error.split()))]
    if document.front_matter is None:
        return None, [("E-FRONTMATTER-MISSING", "expected leading YAML front matter")]
    if not isinstance(document.metadata, dict):
        return None, [("E-FRONTMATTER-INVALID", "front matter must be a YAML mapping")]
    return document.metadata, []


def _check_keys(data: dict[object, object]) -> Problems:
    return [
        ("E-UNKNOWN-KEY", f"unknown front matter key {key!r}")
        for key in data
        if not isinstance(key, str) or (key not in _KEYS and not key.startswith("x-"))
    ]


def _check_id(data: dict[object, object], filename: str, ids: Counter[str] | None) -> tuple[str | None, Problems]:
    """`ids` of None skips the duplicate check."""
    identifier = _identifier(data.get("id"), portable=True)
    if identifier is None:
        return None, [("E-ID-FORMAT", "id must be a portable lowercase kebab-case identifier of at most 64 characters")]
    problems: Problems = []
    if filename != f"{identifier}.md":
        problems.append(("E-ID-FILENAME", f"id {identifier!r} does not match filename {filename!r}"))
    if ids is not None and ids[identifier] > 1:
        problems.append(("E-ID-DUPLICATE", f"id {identifier!r} occurs more than once"))
    return identifier, problems


def _check_summary(data: dict[object, object]) -> tuple[str | None, Problems]:
    summary = _single_line(data.get("summary"))
    if summary is None or len(summary) > 200:
        return summary, [("E-SUMMARY", "summary must be a nonempty single line of at most 200 characters")]
    return summary, []


def _check_category(data: dict[object, object], config: ProjectConfig | None) -> tuple[str | None, Problems]:
    """`config` of None skips the check against the project's categories."""
    category = _identifier(data.get("category"))
    if category is None or (config is not None and category not in config.categories):
        return category, [("E-CATEGORY-UNKNOWN", f"invalid or unknown category {data.get('category')!r}")]
    return category, []


def _check_tags(data: dict[object, object]) -> tuple[list[str], Problems]:
    raw_tags = data.get("tags")
    if not isinstance(raw_tags, list) or not raw_tags:
        return [], [("E-TAGS", "tags must be a nonempty list")]
    tags: list[str] = []
    problems: Problems = []
    for value in raw_tags:
        tag = _identifier(value, limit=64)
        if tag is None:
            message = f"invalid tag {value!r}; expected a lowercase kebab-case identifier of at most 64 characters"
            problems.append(("E-TAGS", message))
        else:
            tags.append(tag)
    return tags, problems


def _check_related(
    data: dict[object, object], identifier: str | None, ids: Counter[str] | None
) -> tuple[tuple[str, ...] | None, Problems]:
    """`ids` of None skips the self/unknown check."""
    if "related" not in data:
        return None, []
    raw_related = data["related"]
    if not isinstance(raw_related, list):
        return None, [("E-RELATED-UNKNOWN", "related must be a list of Tip IDs")]
    related: list[str] = []
    problems: Problems = []
    for value in raw_related:
        target = _identifier(value, portable=True)
        if target is None:
            problems.append(("E-RELATED-UNKNOWN", f"invalid related Tip ID {value!r}"))
            continue
        related.append(target)
        if ids is not None and (target == identifier or target not in ids):
            problems.append(("E-RELATED-UNKNOWN", f"related Tip {target!r} is self or unknown"))
    return tuple(related), problems


def _check_applies_to(data: dict[object, object], config: ProjectConfig | None) -> tuple[dict[str, str], Problems]:
    """`config` of None skips the check against the project's subjects."""
    raw_versions = data.get("applies_to")
    if not isinstance(raw_versions, dict):
        return {}, [("E-APPLIES-TO", "applies_to must be a mapping")]
    applies_to: dict[str, str] = {}
    problems: Problems = []
    for value, spec in raw_versions.items():
        subject = _identifier(value)
        if subject is None:
            problems.append(("E-APPLIES-TO", f"invalid subject key {value!r}"))
        elif config is not None and subject not in config.subjects:
            problems.append(("E-SUBJECT-UNKNOWN", f"unknown subject {subject!r}"))
        version = _single_line(spec)
        if version is None:
            problems.append(("E-APPLIES-TO", f"version for {value!r} must be a nonempty single-line string"))
        if subject is not None and version is not None:
            applies_to[subject] = version
    return applies_to, problems


def _validate_metadata(
    document: Document,
    config: ProjectConfig | None = None,
    ids: Counter[str] | None = None,
) -> tuple[TipMetadata | None, Diagnostics]:
    """Validate front matter; problems are reported in field order.

    `config` and `ids` are None when validating a single installed Tip, which has no project to
    check categories, subjects, duplicates, or related IDs against.
    """
    data, problems = _check_frontmatter(document)
    if data is None:
        return None, [Diagnostic(document.path, 1, code, message) for code, message in problems]
    problems.extend(_check_keys(data))
    identifier, found = _check_id(data, document.path.name, ids)
    problems.extend(found)
    summary, found = _check_summary(data)
    problems.extend(found)
    category, found = _check_category(data, config)
    problems.extend(found)
    tags, found = _check_tags(data)
    problems.extend(found)
    related, found = _check_related(data, identifier, ids)
    problems.extend(found)
    applies_to, found = _check_applies_to(data, config)
    problems.extend(found)
    errors = [Diagnostic(document.path, 1, code, message) for code, message in problems]
    if errors or identifier is None or summary is None or category is None:
        return None, errors
    return TipMetadata(identifier, summary, category, tuple(tags), related, applies_to), errors


def validate_metadata(document: Document) -> tuple[TipMetadata | None, Diagnostics]:
    return _validate_metadata(document)


def validate_tip_metadata(
    document: Document,
    config: ProjectConfig,
    ids: Counter[str],
) -> tuple[TipMetadata | None, Diagnostics]:
    return _validate_metadata(document, config, ids)


def count_ids(documents: list[Document]) -> Counter[str]:
    ids: Counter[str] = Counter()
    for document in documents:
        if isinstance(document.metadata, dict):
            identifier = _identifier(document.metadata.get("id"), portable=True)
            if identifier is not None:
                ids[identifier] += 1
    return ids
