import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from onetips.core.config import default_config
from onetips.core.rules.body import validate_body
from onetips.core.rules.metadata import validate_metadata, validate_tip_metadata
from onetips.core.tip import Document, Heading


def document(headings: list[Heading], lines: list[str]) -> Document:
    return Document(Path("tip.md"), lines, None, None, None, 0, headings, [], [], set(), [])


class CoreRuleTests(unittest.TestCase):
    def test_missing_checklist_section_is_reported_without_touching_files(self) -> None:
        config = default_config("demo")
        headings = [
            Heading("Title", "Title", 1, True, 0),
            Heading(config.sections["when"], config.sections["when"], 2, True, 2),
            Heading(config.sections["approach"], config.sections["approach"], 2, True, 4),
            Heading(config.sections["pitfalls"], config.sections["pitfalls"], 2, True, 6),
        ]
        lines = ["# Title\n", "\n", "## When to Use\n", "\n", "## Recommended Approach\n", "\n", "## Pitfalls\n"]
        with mock.patch("builtins.open", side_effect=AssertionError("core rules must not open files")):
            title, diagnostics = validate_body(document(headings, lines), config)
        self.assertEqual(title, "Title")
        self.assertEqual([(item.code, item.line) for item in diagnostics], [("E-SECTION-MISSING", 1)])
        self.assertIn("Checklist", diagnostics[0].message)


def tip_document(metadata: object, name: str = "tip.md") -> Document:
    return Document(Path(name), [], "front matter", metadata, None, 0, [], [], [], set(), [])


class MetadataRuleTests(unittest.TestCase):
    def test_every_field_problem_is_reported_in_field_order(self) -> None:
        data = {"foo": 1, "id": "Bad_ID", "summary": "", "tags": [], "related": "x", "applies_to": []}
        metadata, diagnostics = validate_tip_metadata(tip_document(data), default_config("demo"), Counter())
        self.assertIsNone(metadata)
        self.assertEqual(
            [item.code for item in diagnostics],
            [
                "E-UNKNOWN-KEY",
                "E-ID-FORMAT",
                "E-SUMMARY",
                "E-CATEGORY-UNKNOWN",
                "E-TAGS",
                "E-RELATED-UNKNOWN",
                "E-APPLIES-TO",
            ],
        )
        self.assertEqual({item.line for item in diagnostics}, {1})

    def test_valid_metadata_without_project_context_skips_project_checks(self) -> None:
        data = {"id": "tip", "summary": "One line.", "category": "anything", "tags": ["a"], "applies_to": {"sdk": "*"}}
        metadata, diagnostics = validate_metadata(tip_document(data))
        self.assertEqual(diagnostics, [])
        assert metadata is not None
        self.assertIsNone(metadata.related)
        self.assertEqual((metadata.id, metadata.tags, metadata.applies_to), ("tip", ("a",), {"sdk": "*"}))

    def test_related_to_self_or_unknown_tip_is_reported(self) -> None:
        data = {
            "id": "tip",
            "summary": "One line.",
            "category": "general",
            "tags": ["a"],
            "related": ["tip", "ghost"],
            "applies_to": {},
        }
        _, diagnostics = validate_tip_metadata(tip_document(data), default_config("demo"), Counter({"tip": 1}))
        self.assertEqual([item.code for item in diagnostics], ["E-RELATED-UNKNOWN", "E-RELATED-UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
