import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

import yaml


class ScaffoldTests(unittest.TestCase):
    env: ClassVar[dict[str, str]] = dict(os.environ, PYTHONUTF8="1")

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "onetips", *args],
            cwd=cwd or self.root,
            env=self.env,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    def assert_failed(self, result: subprocess.CompletedProcess[str], detail: str) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(detail, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_init_and_new_with_localized_config(self) -> None:
        result = self.cli("init", "nested path/tips", "--name", "acme-tips")
        self.assertEqual(result.returncode, 0, result.stderr)
        project = self.root / "nested path" / "tips"
        skill = project / "skills" / "acme-tips"
        references = skill / "references"
        self.assertEqual(list(references.iterdir()), [])
        self.assertEqual(
            {p.relative_to(project).as_posix() for p in project.rglob("*") if p.is_file()},
            {"README.md", "onetips.yaml", "skills/acme-tips/SKILL.md", "skills/acme-tips/INDEX.md"},
        )
        self.assertIn("(skills/acme-tips/INDEX.md)", (project / "README.md").read_text(encoding="utf-8"))
        package = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(yaml.safe_load(package.split("---", 2)[1])["name"], "acme-tips")
        self.assertIn("[INDEX.md](INDEX.md)", package)
        index = skill / "INDEX.md"
        initial_index = index.read_bytes()
        self.assertIn(b"0 tips.", initial_index)
        self.assertIn(b"- `checklist`: Checklist\n", initial_index)

        config = project / "onetips.yaml"
        values = yaml.safe_load(config.read_text(encoding="utf-8"))
        self.assertEqual(values["format"], 1)
        self.assertEqual(values["categories"], [{"id": "general", "title": "General"}])
        values["categories"] = [{"id": "networking", "title": "Networking"}]
        values["sections"]["checklist"] = "檢查清單"
        config.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
        result = self.cli("new", "retry-with-backoff", "--category", "networking", cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)
        tip = (references / "retry-with-backoff.md").read_bytes()
        self.assertNotIn(b"\r", tip)
        self.assertTrue(tip.endswith(b"- [ ]\n"))
        _, header, body = tip.decode().split("---", 2)
        self.assertEqual(
            yaml.safe_load(header),
            {
                "id": "retry-with-backoff",
                "summary": "",
                "category": "networking",
                "tags": [],
                "related": [],
                "applies_to": {},
            },
        )
        self.assertEqual(
            [line for line in body.splitlines() if line.startswith("#")],
            [
                "#",
                "## When to Use",
                "## Recommended Approach",
                "## Pitfalls",
                "## 檢查清單",
            ],
        )
        self.assertEqual(index.read_bytes(), initial_index)

    def test_init_reports_all_conflicts_before_writing(self) -> None:
        for name in ("README.md", "onetips.yaml"):
            (self.root / name).write_bytes(b"existing")
        result = self.cli("init", "--name", "acme-tips")
        self.assert_failed(result, "README.md")
        self.assertIn("onetips.yaml", result.stderr)
        self.assertFalse((self.root / "skills").exists())
        self.assertEqual((self.root / "onetips.yaml").read_bytes(), b"existing")
        self.assertEqual((self.root / "README.md").read_bytes(), b"existing")

    def test_init_rejects_invalid_name_and_blocked_directory(self) -> None:
        self.assert_failed(self.cli("init", "tips", "--name", "../escape"), "name")
        self.assertEqual(list(self.root.iterdir()), [])
        (self.root / "skills").write_bytes(b"existing")
        self.assert_failed(self.cli("init", "--name", "acme-tips"), "skills")
        self.assertEqual(list(self.root.iterdir()), [self.root / "skills"])

    def test_new_rejects_errors_without_touching_project(self) -> None:
        self.assert_failed(self.cli("new", "tip", "--category", "general"), "project root")
        result = self.cli("init", "--name", "acme-tips")
        self.assertEqual(result.returncode, 0, result.stderr)
        skill = self.root / "skills" / "acme-tips"
        references = skill / "references"
        tip = references / "tip.md"
        tip.write_bytes(b"existing")
        index = (skill / "INDEX.md").read_bytes()
        for slug, category, error in (
            ("tip", "general", "conflicting path"),
            ("../escape", "general", "id"),
            ("valid", "unknown", "unknown category"),
        ):
            with self.subTest(slug=slug, category=category):
                self.assert_failed(self.cli("new", slug, "--category", category), error)
        config = self.root / "onetips.yaml"
        with config.open("a", encoding="utf-8") as file:
            file.write("name: another-skill\n")
        self.assert_failed(self.cli("new", "valid", "--category", "general"), "duplicate key 'name'")
        self.assertEqual(list(references.iterdir()), [tip])
        self.assertEqual(tip.read_bytes(), b"existing")
        self.assertEqual((skill / "INDEX.md").read_bytes(), index)

    def test_dangling_file_link_is_a_conflict(self) -> None:
        target = self.root / "missing.md"
        link = self.root / "README.md"
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self.assert_failed(self.cli("init", "--name", "acme-tips"), "README.md")
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())
        self.assertFalse((self.root / "onetips.yaml").exists())
