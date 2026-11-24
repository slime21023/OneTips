import tempfile
import unittest
from pathlib import Path

from onetips.adapters.markdown import read_document

SOURCE = """---
id: tip
---
# Title

## When

Text with a [link](other.md#part) and <a id="x"></a> anchor.

```python status=tested
## fake heading
print(1)
```

- [ ] item
"""


class ReadDocumentTests(unittest.TestCase):
    def test_collects_structure_with_physical_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tip.md"
            path.write_text(SOURCE, encoding="utf-8", newline="\n")
            document = read_document(path)
        self.assertEqual(
            [(h.text, h.level, h.top_level, h.start) for h in document.headings],
            [("Title", 1, True, 3), ("When", 2, True, 5)],
        )
        self.assertEqual(len(document.fences), 1)
        fence = document.fences[0]
        self.assertEqual((fence.snippet.language, fence.snippet.status, fence.start), ("python", "tested", 9))
        self.assertEqual([(link.destination, link.line) for link in document.links], [("other.md#part", 8)])
        self.assertEqual(document.explicit_anchors, {"x"})
        self.assertEqual(document.checklist_items, [14])
        self.assertEqual(document.body_start, 3)


if __name__ == "__main__":
    unittest.main()
