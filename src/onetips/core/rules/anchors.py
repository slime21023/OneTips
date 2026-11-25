from __future__ import annotations

from unicodedata import category

from onetips.core.tip import Document

_STRIPPED_CATEGORIES = {"No", "Pe", "Pf", "Pi", "Ps", "Po", "Pd"}


def heading_slug(title: str) -> str:
    """GitHub-style heading slug using CPython's Unicode character database.

    Keeps spaces (as `-`), hyphens, letters, and remaining non-symbol/control/separator
    characters (excluding Unicode categories starting with S/C/Z and punctuation/other-number).
    """
    return "".join(
        "-" if char == " " else char
        for char in title.lower()
        if char in " -"
        or char.isalpha()
        or char.islower()
        or char.isupper()
        or ((kind := category(char)) not in _STRIPPED_CATEGORIES and kind[0] not in "SCZ")
    )


def heading_anchors(document: Document) -> set[str]:
    slugs: dict[str, int] = {}
    for heading in document.headings:
        base = heading_slug(heading.display)
        slug = base
        while slug in slugs:
            slugs[base] += 1
            slug = f"{base}-{slugs[base]}"
        slugs[slug] = 0
    return slugs.keys() | document.explicit_anchors
