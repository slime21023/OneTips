"""Freeze CLI behavior (exit code, stdout, stderr) so refactors cannot change it silently.

Regenerate only deliberately: ONETIPS_WRITE_SNAPSHOTS=1 python -m unittest tests.test_snapshots
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MINIMAL = FIXTURES / "minimal"
SNAPSHOTS = FIXTURES / "snapshots"
SKILL = Path("skills/acme-tips")
RETRY = "retry-with-backoff"
SCRATCH = re.compile(r"\S*onetips snippets [^/\\\s]+")
ROOT_PATH = re.compile(r"<ROOT>[^\s:]*")


def normalize(text: str, root: Path) -> str:
    text = text.replace("\r\n", "\n")
    for spelling in (str(root), root.as_posix(), str(root).replace("\\", "\\\\")):
        text = text.replace(spelling, "<ROOT>")
    text = ROOT_PATH.sub(lambda match: match.group().replace("\\", "/"), text)
    return SCRATCH.sub("<SCRATCH>", text)


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="snapshot")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("PYTHONPATH", None)

    def run_cli(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, "-m", "onetips", *args],
            cwd=cwd,
            env=self.env,
            check=False,
            capture_output=True,
            timeout=60,
        )
        stdout = normalize(result.stdout.decode("utf-8"), self.root)
        stderr = normalize(result.stderr.decode("utf-8"), self.root)
        return f"exit={result.returncode}\n--- stdout ---\n{stdout}--- stderr ---\n{stderr}"

    def check_snapshot(self, name: str, actual: str) -> None:
        path = SNAPSHOTS / f"{name}.txt"
        if os.environ.get("ONETIPS_WRITE_SNAPSHOTS") == "1":
            SNAPSHOTS.mkdir(exist_ok=True)
            path.write_text(actual, encoding="utf-8", newline="\n")
            return
        self.assertTrue(path.exists(), f"missing snapshot {path.name}")
        self.assertEqual(path.read_text(encoding="utf-8"), actual, name)

    def project_commands(self, name: str, project: Path, extra: dict[str, list[str]]) -> None:
        commands = {"check": ["check"], "index-check": ["index", "--check"], "snippets": ["snippets"], **extra}
        for label, args in commands.items():
            with self.subTest(case=name, command=label):
                self.check_snapshot(f"{name}--{label}", self.run_cli(project, *args))

    def test_minimal_project_and_queries(self) -> None:
        project = self.root / "minimal"
        shutil.copytree(MINIMAL, project)
        skill = (project / SKILL).as_posix()
        self.project_commands("minimal", project, {})
        queries = {
            "verify": ["verify", skill],
            "find-all": ["find", "--skill-dir", skill],
            "find-tag-json": ["find", "--skill-dir", skill, "--tag", "retry", "--json"],
            "find-keyword": ["find", "--skill-dir", skill, "--keyword", "backoff"],
            "show-metadata": ["show", "--skill-dir", skill, RETRY, "--metadata"],
            "show-metadata-json": ["show", "--skill-dir", skill, RETRY, "--metadata", "--json"],
            "show-checklist": ["show", "--skill-dir", skill, RETRY, "--section", "checklist"],
            "show-code-json": ["show", "--skill-dir", skill, RETRY, "--code", "--json"],
            "show-missing-tip": ["show", "--skill-dir", skill, "absent-tip", "--metadata"],
        }
        for name, args in queries.items():
            with self.subTest(case=name):
                self.check_snapshot(f"minimal--{name}", self.run_cli(self.root, *args))

    def test_invalid_recipes(self) -> None:
        for recipe in sorted(FIXTURES.glob("invalid-*.json")):
            case = json.loads(recipe.read_text(encoding="utf-8"))
            project = self.root / recipe.stem
            shutil.copytree(MINIMAL, project)
            target = project / case["path"]
            text = target.read_text(encoding="utf-8")
            self.assertEqual(text.count(case["before"]), 1, recipe.name)
            target.write_text(text.replace(case["before"], case["after"]), encoding="utf-8", newline="\n")
            self.project_commands(recipe.stem, project, {"verify": ["verify", (project / SKILL).as_posix()]})

    def test_damaged_indexes(self) -> None:
        for name in ("missing-entry", "broken-reference", "garbage", "absent"):
            project = self.root / name
            shutil.copytree(MINIMAL, project)
            skill = project / SKILL
            index = skill / "INDEX.md"
            original = index.read_text(encoding="utf-8")
            if name == "missing-entry":
                lines = [line for line in original.split("\n") if not line.startswith(f"|[{RETRY}](")]
                index.write_text("\n".join(lines).replace("2 tips.", "1 tips."), encoding="utf-8", newline="\n")
            elif name == "broken-reference":
                (skill / "references" / f"{RETRY}.md").unlink()
            elif name == "garbage":
                index.write_text("not a generated index\n", encoding="utf-8", newline="\n")
            else:
                index.unlink()
            with self.subTest(case=name):
                self.check_snapshot(f"damaged-{name}--verify", self.run_cli(self.root, "verify", skill.as_posix()))
                self.check_snapshot(f"damaged-{name}--find", self.run_cli(self.root, "find", "--skill-dir", skill.as_posix()))


if __name__ == "__main__":
    unittest.main()
