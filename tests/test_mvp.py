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
SKILL = Path("skills/acme-tips")
RETRY = "retry-with-backoff"
RETRY_PATH = Path("references") / f"{RETRY}.md"
SECOND_PATH = Path("references/idempotency-keys.md")
SUMMARY = "Cap retry attempts and delay for transient Acme SDK failures."
VERSION = ">=2.0 <3.0"
CHECKLIST = "## 檢查清單\n\n- [ ] Limit both attempts and delay.\n"
TESTED_CODE = (
    "def retry_delay(attempt: int) -> int:\n"
    "    return min(2 ** attempt, 8)\n\n\n"
    "assert [retry_delay(i) for i in range(6)] == [1, 2, 4, 8, 8, 8]\n"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def inventory(root: Path) -> dict[str, bytes]:
    return {item.relative_to(root).as_posix(): item.read_bytes() for item in root.rglob("*") if item.is_file()}


class MvpTests(unittest.TestCase):
    def setUp(self) -> None:
        shared = os.environ.get("ONETIPS_TEST_WORK_DIR")
        if shared:
            self.root = Path(shared).resolve() / self._testMethodName
            self.root.mkdir()
            self.addCleanup(shutil.rmtree, self.root)
        else:
            temp = tempfile.TemporaryDirectory(prefix="OneTips test ")
            self.addCleanup(temp.cleanup)
            self.root = Path(temp.name).resolve()
        self.project = self.root / "author project"
        self.skill = self.project / SKILL
        self.index = self.skill / "INDEX.md"
        self.retry = self.skill / RETRY_PATH
        shutil.copytree(MINIMAL, self.project)
        self.python = Path(os.environ.get("ONETIPS_TEST_PYTHON", sys.executable)).absolute()
        self.env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("PYTHONPATH", None)
        self.env["PATH"] = str(self.python.parent) + os.pathsep + self.env["PATH"]

    def cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(self.python), "-m", "onetips", *args],
            cwd=cwd or self.project,
            env=self.env,
            check=False,
            capture_output=True,
            timeout=45,
        )

    def query(self, command: str, *args: str) -> subprocess.CompletedProcess[bytes]:
        result = self.cli(command, "--skill-dir", str(self.skill.relative_to(self.root)), *args, cwd=self.root)
        capture = os.environ.get("ONETIPS_TEST_QUERY_CAPTURE")
        if capture:
            observation = [self._testMethodName, command, args, result.returncode, result.stdout.hex(), result.stderr.hex()]
            with Path(capture).open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(observation, ensure_ascii=False) + "\n")
        return result

    def ok(self, result: subprocess.CompletedProcess[bytes]) -> bytes:
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertEqual(result.stderr, b"")
        return result.stdout

    def query_failed(self, result: subprocess.CompletedProcess[bytes], code: int = 1) -> bytes:
        self.assertEqual(result.returncode, code, (result.stdout, result.stderr))
        self.assertEqual(result.stdout, b"")
        self.assertTrue(result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        return result.stderr

    def diagnostic(
        self,
        result: subprocess.CompletedProcess[bytes],
        path: Path,
        code: str,
        *,
        line: int | None = None,
        exit_code: int = 1,
    ) -> str:
        err = result.stderr.decode("utf-8").replace("\\", "/")
        self.assertEqual(result.returncode, exit_code, (result.stdout, err))
        self.assertNotIn("Traceback", err)
        number = str(line) if line is not None else r"[1-9][0-9]*"
        self.assertRegex(err, rf"(?m)^(?:[^\n]*[/])?{re.escape(path.as_posix())}:{number}: {code} .+$")
        return err

    def replace(self, path: Path, before: str, after: str) -> None:
        text = read(path)
        self.assertEqual(text.count(before), 1, (path, before))
        write(path, text.replace(before, after))

    def symlink(self, path: Path, target: Path, *, directory: bool = False) -> None:
        try:
            path.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlinks not available: {error}")

    def test_index_reproducible_and_stale_with_diff(self) -> None:
        golden = self.index.read_bytes()
        self.assertTrue(golden.endswith(b"|\n"))
        self.assertNotIn(b"\r", golden)
        self.assertIn(b"tested 1, compiled 0, unverified 2", golden)
        self.assertIn(b"tested 0, compiled 1, unverified 0", golden)
        self.index.unlink()
        for _ in range(2):
            self.ok(self.cli("index"))
            self.assertEqual(self.index.read_bytes(), golden)
        self.ok(self.cli("index", "--check"))
        self.assertIn(b"0 errors, 0 warnings", self.ok(self.cli("check")))

        changed = "Use capped delays and a fixed attempt limit."
        self.replace(self.retry, SUMMARY, changed)
        check = self.cli("index", "--check")
        self.assertEqual(check.returncode, 1, (check.stdout, check.stderr))
        diff = check.stdout + check.stderr
        self.assertRegex(diff, rb"(?m)^-\|[^\r\n]+" + re.escape(SUMMARY.encode()))
        self.assertRegex(diff, rb"(?m)^\+\|[^\r\n]+" + re.escape(changed.encode()))
        self.assertEqual(self.index.read_bytes(), golden)
        self.diagnostic(self.cli("check"), Path("INDEX.md"), "E-INDEX-STALE")
        self.ok(self.cli("index"))
        self.ok(self.cli("check"))
        results = self.ok(self.cli("find", "--skill-dir", str(self.skill), "--tag", "retry", "--json"))
        self.assertEqual(json.loads(results)[0]["summary"], changed)

    def test_invalid_fixture_recipes(self) -> None:
        recipes = sorted(FIXTURES.glob("invalid-*.json"))
        self.assertEqual(len(recipes), 17)
        exact_tokens = {
            "E-SECTION-ORDER": "## Recommended Approach",
            "E-SECTION-DUPLICATE": "## Pitfalls",
            "E-CHECKLIST-EMPTY": "## 檢查清單",
            "E-CODE-LANG": "```\n## 檢查清單",
            "E-CODE-STATUS": "```python status=planned",
            "E-LINK-BROKEN": "Retry only transient failures",
            "E-LINK-ANCHOR": "Retry only transient failures",
            "E-LINK-ESCAPES-SKILL": "Retry only transient failures",
            "E-SNIPPET-FAILED": "```python status=tested",
            "E-SNIPPET-NO-COMMAND": "```python status=tested",
        }
        for recipe in recipes:
            with self.subTest(recipe=recipe.name):
                case = json.loads(read(recipe))
                project = self.root / recipe.stem
                shutil.copytree(MINIMAL, project)
                path = Path(case["path"])
                self.replace(project / path, case["before"], case["after"])
                if path == Path("onetips.yaml") and case["command"] == "snippets":
                    path = SKILL / RETRY_PATH
                code = case["code"]
                token = exact_tokens.get(code)
                line = read(project / path).rsplit(token, 1)[0].count("\n") + 1 if token else 1
                result = self.cli(case["command"], cwd=project)
                err = self.diagnostic(result, path, code, line=line)
                self.assertRegex(err, r"\b[1-9][0-9]* errors, [0-9]+ warnings\b")

    def test_missing_index_entry_broken_reference_and_index_cannot_be_repaired_by_verify(self) -> None:
        original = read(self.index)
        missing_entry = "\n".join(line for line in original.split("\n") if not line.startswith(f"|[{RETRY}]("))
        write(self.index, missing_entry.replace("2 tips.", "1 tips."))
        result = self.cli("verify", str(self.skill), cwd=self.root)
        self.assertIn(RETRY_PATH.name, self.diagnostic(result, Path("INDEX.md"), "E-INDEX-MISSING-ENTRY"))
        self.assertEqual(result.stdout, b"")
        write(self.index, original)
        self.retry.unlink()
        self.diagnostic(self.cli("verify", str(self.skill), cwd=self.root), Path("INDEX.md"), "E-LINK-BROKEN")
        self.assertEqual(read(self.index), original)
        write(self.index, "not a generated index\n")
        self.diagnostic(self.cli("verify", str(self.skill), cwd=self.root), Path("INDEX.md"), "E-INDEX-FORMAT")
        self.index.unlink()
        result = self.cli("verify", str(self.skill), cwd=self.root)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(b"INDEX.md", result.stderr)
        self.assertFalse(self.index.exists())

    def test_config_errors_are_usage_errors_and_verify_ignores_config(self) -> None:
        config = self.project / "onetips.yaml"
        original = read(config)
        errors = [
            original.replace("format: 1", "format: 9"),
            original + "name: duplicate\n",
            original.replace("    ext: py", "    ext: .py"),
            original + "    timeout: true\n",
        ]
        for invalid in errors:
            with self.subTest(config=invalid):
                write(config, invalid)
                self.diagnostic(self.cli("check"), Path(config.name), "E-CONFIG", exit_code=2)
                self.assertRegex(
                    self.ok(self.cli("verify", str(self.skill), cwd=self.root)), rb"^computedHash: [0-9a-f]{64}\r?\n$"
                )
        config.unlink()
        self.assertEqual(self.cli("index").returncode, 2)

    def test_links_use_rendered_unicode_slugs_and_reference_definitions(self) -> None:
        other = self.skill / SECOND_PATH
        with other.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write('\n### Étape `clé`\n\n### Étape clé\n\n### Étape clé-1\n\n<a id="explicit-name"></a>\n')
        with self.retry.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                "\n[First][target] [Second](idempotency-keys.md#étape-clé-1) "
                "[Suffix](idempotency-keys.md#étape-clé-1-1) "
                "[Explicit](idempotency-keys.md#explicit-name) "
                "[External](https://example.invalid/no-fetch)\n\n"
                "[target]: idempotency-keys.md?ignored=true#%C3%A9tape-cl%C3%A9\n"
            )
        self.ok(self.cli("check"))
        self.replace(
            self.retry, "[target]: idempotency-keys.md?ignored=true#%C3%A9tape-cl%C3%A9", "[target]: %2e%2e/%2e%2e/nonexistent.md"
        )
        self.diagnostic(self.cli("check"), Path(self.retry.name), "E-LINK-ESCAPES-SKILL")

    def test_source_index_never_overwrites_a_symlink(self) -> None:
        destination = self.root / "existing.md"
        destination.write_bytes(b"must not be overwritten\n")
        self.index.unlink()
        self.symlink(self.index, destination)
        result = self.cli("index")
        self.assertNotEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertTrue(self.index.is_symlink())
        self.assertEqual(destination.read_bytes(), b"must not be overwritten\n")

    def test_warning_only_is_success(self) -> None:
        path = self.skill / "SKILL.md"
        write(path, read(path) + "\n" * 501)
        result = self.cli("check")
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        out = result.stdout + result.stderr
        self.assertEqual(out.count(b"W-SKILL-LONG"), 1)
        self.assertIn(b"0 errors, 1 warnings", out)

    def test_upstream_hash_vectors_and_normalization(self) -> None:
        vectors = [
            ({}, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
            ({"SKILL.md": b"# hi\n"}, "93c36952d8843b33e68ae970ebabcc03e1687c9bb0dd1ecaf357060318952f55"),
            ({"SKILL.md": b"a\n", "docs/b.md": b"b\n"}, "b22c4d22aa319d2924312fa18fcbfedc88fa89c74dbd8f298c683e1caf7b7f24"),
            (
                {
                    "SKILL.md": b"a\r\n",
                    "docs/b.md": b"b\r\n",
                    "docs/metadata.json": b"ignored",
                    ".git/skip": b"ignored",
                    "docs/__pycache__/skip": b"ignored",
                    "__pypackages__/skip": b"ignored",
                },
                "b22c4d22aa319d2924312fa18fcbfedc88fa89c74dbd8f298c683e1caf7b7f24",
            ),
        ]
        for number, (files, expected) in enumerate(vectors):
            folder = self.root / f"hash-vector-{number}"
            folder.mkdir()
            for relative, data in files.items():
                target = folder / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            result = subprocess.run(
                [
                    str(self.python),
                    "-c",
                    "from onetips.adapters.hashing import computed_hash; from pathlib import Path; "
                    "import sys; print(computed_hash(Path(sys.argv[1])))",
                    str(folder),
                ],
                cwd=self.root,
                env=self.env,
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(self.ok(result).strip().decode(), expected)

    def test_snippets_selection_and_failure_does_not_execute_unselected_tip(self) -> None:
        initial = inventory(self.project)
        self.ok(self.cli("snippets"))
        self.assertEqual(inventory(self.project), initial)
        self.replace(self.retry, "[1, 2, 4, 8, 8, 8]", "[0, 2, 4, 8, 8, 8]")
        self.ok(self.cli("check"))
        self.ok(self.cli("snippets", "--id", "idempotency-keys"))
        self.diagnostic(self.cli("snippets", "--id", RETRY), Path(self.retry.name), "E-SNIPPET-FAILED", line=22)
        for bad_id in ("does-not-exist", "../outside"):
            result = self.cli("snippets", "--id", bad_id)
            self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
            self.assertNotIn(b"E-SNIPPET-FAILED", result.stderr)

    def test_snippets_extraction_and_placeholders_with_spaces(self) -> None:
        temp = self.root / "snippet extraction with spaces"
        temp.mkdir()
        self.env.update(TMPDIR=str(temp), TEMP=str(temp), TMP=str(temp))
        self.replace(self.project / "onetips.yaml", "    test: python {file}", "    test: python {file} {dir}")
        self.replace(
            self.retry,
            "def retry_delay(attempt: int) -> int:",
            "import os\nimport sys\nfrom pathlib import Path\n\n"
            "source = Path(__file__).resolve()\n"
            "assert source == Path(os.environ['ONETIPS_SNIPPET_FILE']).resolve()\n"
            "assert source.parent == Path(sys.argv[1]).resolve()\n"
            "assert source.parent == Path(os.environ['ONETIPS_SNIPPET_DIR']).resolve()\n"
            "assert 'snippet extraction with spaces' in source.parts\n"
            "assert b'\\r' not in source.read_bytes()\n\n"
            "def retry_delay(attempt: int) -> int:",
        )
        self.ok(self.cli("snippets", "--id", RETRY))
        self.assertEqual(list(temp.iterdir()), [])

    def test_snippets_failed_compile_prevents_test(self) -> None:
        self.replace(self.retry, "    return min(2 ** attempt, 8)", "    return )")
        config = self.project / "onetips.yaml"
        self.replace(
            config, "    test: python {file}", "    test: python -c \"from pathlib import Path; Path('ran-test').touch()\""
        )
        err = self.diagnostic(self.cli("snippets", "--id", RETRY), Path(self.retry.name), "E-SNIPPET-FAILED", line=22)
        self.assertIn("compile", err.lower())
        self.assertFalse((self.project / "ran-test").exists())

    def test_snippets_nonzero_exit_and_timeout(self) -> None:
        config = self.project / "onetips.yaml"
        original = read(config)
        for command, detail in (('python -c "raise SystemExit(17)"', "17"), ('python -c "import time; time.sleep(2)"', "tim")):
            with self.subTest(command=command):
                write(config, original.replace("test: python {file}", "test: " + command) + "    timeout: 1\n")
                err = self.diagnostic(self.cli("snippets", "--id", RETRY), Path(self.retry.name), "E-SNIPPET-FAILED", line=22)
                self.assertIn(detail, err.lower())

    def test_query_find_reads_only_index_and_combines_filters(self) -> None:
        filters = ("--id", RETRY, "--category", "networking", "--tag", "retry", "--keyword", "TRANSIENT", "--json")
        with_references = self.ok(self.query("find", *filters))
        shutil.rmtree(self.skill / "references")
        (self.project / "onetips.yaml").unlink()
        expected = [
            {
                "id": RETRY,
                "title": "Retry with backoff",
                "summary": SUMMARY,
                "category": "networking",
                "tags": ["retry"],
                "applies_to": f"acme-sdk {VERSION}",
                "path": RETRY_PATH.as_posix(),
            }
        ]
        output = self.ok(self.query("find", *filters))
        self.assertEqual(output, with_references)
        self.assertEqual(json.loads(output), expected)
        self.assertEqual(tuple(json.loads(output)[0]), tuple(expected[0]))
        self.assertTrue(output.endswith(b"\n"))
        self.assertNotIn(b"\r", output)
        output = self.ok(self.query("find", "--json"))
        self.assertEqual([row["id"] for row in json.loads(output)], ["idempotency-keys", RETRY])
        plain = self.ok(self.query("find", "--tag", "retry"))
        self.assertEqual(
            plain.decode().splitlines(),
            [f"- [{RETRY}]({RETRY_PATH.as_posix()}) — Retry with backoff — {SUMMARY} (acme-sdk {VERSION})"],
        )
        self.assertEqual(self.ok(self.query("find", "--id", RETRY, "--tag", "idempotency", "--json")), b"[]\n")
        self.assertEqual(self.ok(self.query("find", "--tag", "Retry")), b"")

    def test_query_metadata_section_code_and_empty_selection(self) -> None:
        (self.skill / SECOND_PATH).unlink()
        (self.project / "onetips.yaml").unlink()
        self.assertEqual(self.ok(self.query("show", RETRY, "--section", "checklist")).decode(), CHECKLIST)
        metadata = self.ok(self.query("show", RETRY, "--metadata", "--json"))
        self.assertEqual(
            json.loads(metadata),
            {
                "id": RETRY,
                "summary": SUMMARY,
                "category": "networking",
                "tags": ["retry"],
                "related": ["idempotency-keys"],
                "applies_to": {"acme-sdk": VERSION},
            },
        )
        self.assertNotIn(b"x-example", metadata)
        raw = self.ok(self.query("show", RETRY, "--metadata"))
        self.assertEqual(raw.decode(), read(self.retry).split("---\n", 2)[1])
        args = (RETRY, "--section", "approach", "--code", "--lang", "python", "--status", "tested")
        code = self.ok(self.query("show", *args, "--json"))
        self.assertEqual(json.loads(code), [{"language": "python", "status": "tested", "code": TESTED_CODE}])
        self.assertEqual(self.ok(self.query("show", *args)).decode(), f"```python status=tested\n{TESTED_CODE}```\n")
        fences = json.loads(self.ok(self.query("show", RETRY, "--code", "--json")))
        self.assertEqual(
            [(f["language"], f["status"]) for f in fences],
            [("python", "tested"), ("text", "unverified"), ("python", "unverified")],
        )
        self.assertEqual(self.ok(self.query("show", RETRY, "--code", "--status", "compiled", "--json")), b"[]\n")
        self.assertEqual(self.ok(self.query("show", RETRY, "--code", "--lang", "ruby")), b"")
        self.query_failed(self.query("show", "idempotency-keys", "--metadata"))

    def test_query_unicode_escaped_delimiters_and_no_side_effects(self) -> None:
        title = "Straße | 避難"
        summary = "Straße | 避難 & [文] _em_ ~tilde~ `tick` *star*"
        self.replace(self.retry, "# Retry with backoff", "# Straße | 避難")
        self.replace(self.retry, SUMMARY, "'" + summary + "'")
        self.replace(
            self.retry,
            "def retry_delay(attempt: int) -> int:",
            "from pathlib import Path\nPath('ran-query').touch()\n\ndef retry_delay(attempt: int) -> int:",
        )
        self.ok(self.cli("index"))
        self.assertIn(rb"\|", self.index.read_bytes())
        initial = inventory(self.root)
        output = self.ok(self.query("find", "--keyword", "STRASSE", "--json"))
        (row,) = json.loads(output)
        self.assertEqual((row["title"], row["summary"]), (title, summary))
        self.assertIn("避難".encode(), output)
        (code,) = json.loads(self.ok(self.query("show", RETRY, "--code", "--status", "tested", "--json")))
        self.assertIn("touch()", code["code"])
        self.assertEqual(inventory(self.root), initial)

    def test_query_malformed_or_missing_index_path_escape_and_usage(self) -> None:
        for args in (
            (),
            ("--metadata", "--section", "when"),
            ("--metadata", "--code"),
            ("--section", "when", "--json"),
            ("--section", "when", "--lang", "python"),
            ("--metadata", "--status", "tested"),
            ("--section", "unknown"),
            ("--code", "--status", "unknown"),
        ):
            with self.subTest(args=args):
                self.query_failed(self.query("show", RETRY, *args), 2)
        self.query_failed(self.query("show", "not-indexed", "--metadata"))
        original = read(self.index)
        self.replace(self.index, f"]({RETRY_PATH.as_posix()})", "](references/../../secret.md)")
        self.query_failed(self.query("find", "--json"))
        self.query_failed(self.query("show", RETRY, "--metadata"))
        write(self.index, original + "not part of the grammar\n")
        self.query_failed(self.query("find", "--json"))
        self.index.unlink()
        self.query_failed(self.query("find", "--json"))
        self.query_failed(self.query("show", RETRY, "--metadata"))

    def test_query_rejects_symlink_escapes(self) -> None:
        external = self.root / "external references"
        external.mkdir()
        (self.skill / "references").rename(external / "references")
        self.symlink(self.skill / "references", external / "references", directory=True)
        self.assertEqual(len(json.loads(self.ok(self.query("find", "--json")))), 2)
        self.query_failed(self.query("show", RETRY, "--section", "when"))
        (self.skill / "references").unlink()
        (self.skill / "references").mkdir()
        self.symlink(self.retry, external / "references" / self.retry.name)
        self.query_failed(self.query("show", RETRY, "--metadata"))


if __name__ == "__main__":
    unittest.main()
