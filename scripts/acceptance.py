"""Exercise the pinned skill installer or build and compare local OneTips wheels."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
MINIMAL = FIXTURES / "minimal"
SKILL_NAME = "acme-tips"
SKILL = Path("skills") / SKILL_NAME
RETRY = "retry-with-backoff"
RETRY_PATH = Path("references") / f"{RETRY}.md"
CHECKLIST = "## 檢查清單\n\n- [ ] Limit both attempts and delay.\n"
INSTALLER_VERSION = "1.9.0"
GIT_URL = "http://127.0.0.1:1/fixtures/acme-tips.git"
TAG = "v0.1.0"


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(
    *command: str, cwd: Path, env: dict[str, str], expected: int = 0, timeout: int = 240
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, cwd=cwd, env=env, check=False, capture_output=True, timeout=timeout)
    if result.returncode != expected:
        raise RuntimeError(
            f"{command!r}: expected exit {expected}, got {result.returncode}\n"
            f"stdout:\n{result.stdout.decode('utf-8', errors='replace')}\n"
            f"stderr:\n{result.stderr.decode('utf-8', errors='replace')}"
        )
    return result


def executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required executable not found: {name}")
    return path


def bash_executable() -> str:
    if os.name == "nt":
        git_bash = Path(executable("git")).resolve().parents[1] / "bin" / "bash.exe"
        if git_bash.is_file():
            return str(git_bash)
    return executable("bash")


def env_for_children() -> dict[str, str]:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return env


def inventory(root: Path) -> dict[str, bytes]:
    files = {}
    for item in root.rglob("*"):
        require(not item.is_symlink(), f"unexpected symlink in --copy installation: {item}")
        if item.is_file():
            files[item.relative_to(root).as_posix()] = item.read_bytes()
    return files


def verify(skill: Path, cwd: Path, env: dict[str, str]) -> str:
    result = run(sys.executable, "-m", "onetips", "verify", str(skill), cwd=cwd, env=env)
    found = re.fullmatch(rb"computedHash: ([0-9a-f]{64})\r?\n", result.stdout)
    if found is None or result.stderr:
        raise RuntimeError(f"unexpected verify output: {result.stdout!r} {result.stderr!r}")
    return found[1].decode("ascii")


def install(source: str, target: Path, env: dict[str, str]) -> tuple[Path, dict]:
    target.mkdir()
    run(executable("git"), "init", "--template=", cwd=target, env=env)
    bun = executable("bun")
    pinned = f"skills@{INSTALLER_VERSION}"
    run(bun, "x", pinned, "add", source, "--skill", SKILL_NAME, "-a", "claude-code", "--copy", "-y", cwd=target, env=env)
    listing = run(bun, "x", pinned, "list", "--json", cwd=target, env=env)
    entries = json.loads(listing.stdout)
    require(len(entries) == 1, f"expected one installed skill: {entries!r}")
    name, status = entries[0]["name"], entries[0]["status"]
    require((name, status) == (SKILL_NAME, "tracked"), f"untracked or incorrect skill: {entries[0]!r}")
    require("Claude Code" in entries[0]["agents"], f"Claude Code missing in listing: {entries[0]!r}")
    installed = Path(entries[0]["path"])
    if not installed.is_absolute():
        installed = target / installed
    expected = target / ".claude" / "skills" / SKILL_NAME
    require(
        installed == expected
        and installed.is_dir()
        and not installed.is_symlink()
        and not installed.is_junction()
        and installed.resolve().is_relative_to(target),
        f"expected the Claude Code copy at {expected}, got {installed}",
    )
    lock = json.loads((target / "skills-lock.json").read_bytes())
    require(lock["version"] == 2, f"expected skills-lock.json v2: {lock!r}")
    require(set(lock["skills"]) == {SKILL_NAME}, f"unexpected lock entries: {lock!r}")
    return installed, lock["skills"][SKILL_NAME]


def reject_escape(skill: Path, cwd: Path, env: dict[str, str]) -> None:
    result = run(sys.executable, "-m", "onetips", "verify", str(skill), cwd=cwd, env=env, expected=1)
    require(
        not result.stdout and b"E-LINK-ESCAPES-SKILL" in result.stderr,
        f"escaping link did not fail verification: {result.stdout!r} {result.stderr!r}",
    )


def assert_copy(installed: Path, target: Path, lock: dict, expected: dict[str, bytes], digest: str, env: dict[str, str]) -> None:
    actual = inventory(installed)
    require(
        actual == expected,
        f"installed files differ from source: paths {sorted(actual)} vs {sorted(expected)}; "
        f"changed {sorted(k for k in actual.keys() & expected.keys() if actual[k] != expected[k])}",
    )
    require(
        verify(installed, target, env) == lock["computedHash"] == digest,
        f"source, installed and lock hashes differ: source {digest}, lock {lock!r}",
    )


def no_cli_lookup(installed: Path) -> None:
    bash = bash_executable()
    if os.name == "nt" and (Path(bash).parent.parent / "usr/bin/awk.exe").exists():
        awk = (Path(bash).parent.parent / "usr/bin/awk.exe").as_posix()
    else:
        awk = executable("awk")
    shell_env = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ}
    shell_env.update(PATH="/onetips-text-tools-only", LC_ALL="C")
    command = r"""
set -eu
for forbidden in python python3 uv onetips jq yq; do
    if command -v "$forbidden" >/dev/null; then exit 4; fi
done
awk=$1
ref=$("$awk" -F '|' '$5 == "retry" {
    sub(/^\[[^]]+\]\(/, "", $2)
    sub(/\)$/, "", $2)
    print $2
}' INDEX.md)
[ "$ref" = references/retry-with-backoff.md ]
heading=$("$awk" 'index($0, "- `checklist`: ") == 1 {
    print substr($0, length("- `checklist`: ") + 1)
}' INDEX.md)
[ -n "$heading" ]
"$awk" -v heading="$heading" '
    /^```/ { fence = !fence }
    fence { next }
    /^## / { selected = ($0 == "## " heading) }
    selected { print }
' "$ref"
"""
    result = run(bash, "--noprofile", "--norc", "-c", command, "text-only", awk, cwd=installed, env=shell_env)
    require(
        result.stdout.decode("utf-8").replace("\r\n", "\n") == CHECKLIST,
        f"text-only lookup returned the wrong section: {result.stdout!r}",
    )
    print("AC-5: text-only installed lookup passed (no OneTips CLI, Python or uv on PATH).", flush=True)


def installed_queries(installed: Path, target: Path, env: dict[str, str]) -> None:
    cli = sys.executable, "-m", "onetips"
    args = "--skill-dir", str(installed)
    result = run(*cli, "find", *args, "--tag", "retry", "--json", cwd=target, env=env)
    rows = json.loads(result.stdout)
    require(
        [(row["id"], row["path"], row["applies_to"]) for row in rows] == [(RETRY, RETRY_PATH.as_posix(), "acme-sdk >=2.0 <3.0")],
        f"unexpected installed query: {rows!r}",
    )
    section = run(*cli, "show", *args, RETRY, "--section", "checklist", cwd=target, env=env)
    require(section.stdout == CHECKLIST.encode(), f"unexpected installed checklist: {section.stdout!r}")


def commit(cwd: Path, env: dict[str, str], message: str) -> str:
    git = executable("git")
    run(git, "-c", "core.autocrlf=false", "add", ".", cwd=cwd, env=env)
    run(
        git,
        "-c",
        "core.autocrlf=false",
        "-c",
        "user.name=OneTips",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        message,
        cwd=cwd,
        env=env,
    )
    return run(git, "rev-parse", "HEAD", cwd=cwd, env=env).stdout.decode("ascii").strip()


def installers(work: Path, remote_source: str | None) -> None:
    env = dict(
        env_for_children(),
        DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        XDG_CONFIG_HOME=str(work / "user-config"),
        XDG_STATE_HOME=str(work / "user-state"),
    )
    env.pop("GIT_CONFIG_COUNT", None)
    env.pop("BASH_ENV", None)
    node = run(executable("node"), "--version", cwd=work, env=env).stdout.decode().strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", node)
    require(match is not None and tuple(map(int, match.groups())) >= (22, 20, 0), f"Node >=22.20 required: {node}")
    smoke = run(bash_executable(), "--noprofile", "--norc", "-c", f"bunx skills@{INSTALLER_VERSION} --version", cwd=work, env=env)
    require(INSTALLER_VERSION in smoke.stdout.decode(), f"unexpected bunx version output: {smoke.stdout!r}")

    source = work / "direct-source"
    shutil.copytree(MINIMAL, source)
    expected = inventory(source / SKILL)
    digest = verify(source / SKILL, source, env)
    target = work / "installed-direct"
    installed, lock = install(str(source), target, env)
    assert_copy(installed, target, lock, expected, digest, env)
    source.rename(work / "direct-source-moved-away")
    assert_copy(installed, target, lock, expected, digest, env)
    no_cli_lookup(installed)
    installed_queries(installed, target, env)
    print(f"AC-4/6: direct copy, lock hash {digest}, and installed queries passed.", flush=True)

    source = work / "tagged-source"
    shutil.copytree(MINIMAL, source)
    git = executable("git")
    run(git, "init", "--template=", cwd=source, env=env)
    tagged_commit = commit(source, env, "Tagged fixture")
    run(git, "tag", TAG, cwd=source, env=env)
    for file in (source / "README.md", source / SKILL / "SKILL.md"):
        with file.open("ab") as stream:
            stream.write(b"\nChanged after tag.\n")
    require(commit(source, env, "Change source after tag") != tagged_commit, "HEAD must differ from the tag")
    require(inventory(source / SKILL) != expected, "HEAD must package different bytes from the tag")
    rewritten = dict(env, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0=f"url.{source.as_uri()}.insteadOf", GIT_CONFIG_VALUE_0=GIT_URL)
    target = work / "installed-tagged"
    installed, lock = install(f"{GIT_URL}#{TAG}", target, rewritten)
    require(lock.get("commit") == tagged_commit and lock.get("ref") == TAG, f"lock did not pin the tag: {lock!r}")
    assert_copy(installed, target, lock, expected, digest, env)
    source.rename(work / "tagged-source-moved-away")
    assert_copy(installed, target, lock, expected, digest, env)
    print(f"AC-4: tagged Git source installed {TAG} ({tagged_commit}), not HEAD.", flush=True)

    source = work / "escaping-source"
    shutil.copytree(MINIMAL, source)
    case = json.loads((FIXTURES / "invalid-escaping-link.json").read_bytes())
    path = source / case["path"]
    contents = path.read_text(encoding="utf-8")
    require(contents.count(case["before"]) == 1, "escape recipe must replace one link")
    path.write_text(contents.replace(case["before"], case["after"]), encoding="utf-8", newline="\n")
    reject_escape(source / SKILL, source, env)
    target = work / "installed-escape"
    installed, _ = install(str(source), target, env)
    reject_escape(installed, target, env)
    print("AC-4: escaping link rejected before and after installation.", flush=True)

    if remote_source:
        target = work / "installed-remote"
        installed, lock = install(remote_source, target, env)
        assert_copy(installed, target, lock, expected, digest, env)
        print(f"AC-4: published source {remote_source} matches fixture and lock hash.", flush=True)


def build_wheel(work: Path, mode: str, env: dict[str, str]) -> Path:
    source = work / f"source-{mode}"
    source.mkdir()
    for name in ("pyproject.toml", "setup.py", "README.md"):
        shutil.copyfile(ROOT / name, source / name)
    shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns("*.egg-info", "__pycache__", "*.so", "*.pyd"))
    build_env = {key: value for key, value in env.items() if key != "ONETIPS_MYPYC"}
    if mode == "native":
        build_env["ONETIPS_MYPYC"] = "1"
    uv = executable("uv")
    wheels = work / f"wheels-{mode}"
    run(uv, "build", "--python", "3.13", "--wheel", "--out-dir", str(wheels), cwd=source, env=build_env)
    (wheel,) = wheels.glob("*.whl")
    require(wheel.name.endswith("-py3-none-any.whl") == (mode == "pure"), f"unexpected wheel tag: {wheel.name}")
    venv = work / f"venv-{mode}"
    run(uv, "venv", "--python", "3.13", str(venv), cwd=work, env=env)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run(uv, "pip", "install", "--python", str(python), str(wheel), cwd=work, env=env)
    print(f"Built and installed {wheel.name}", flush=True)
    return python


def parity(work: Path, pure: Path, native: Path) -> None:
    env = env_for_children()
    result = run(
        sys.executable, str(ROOT / "scripts/benchmark.py"), "--pure", str(pure), "--native", str(native), cwd=work, env=env
    )
    print(result.stdout.decode("utf-8"), end="", flush=True)
    shared = work / "same-test-path"
    shared.mkdir()
    transcripts = []
    for mode, python in (("pure", pure), ("native", native)):
        capture = work / f"query-{mode}.jsonl"
        trial = dict(
            env, ONETIPS_TEST_PYTHON=str(python), ONETIPS_TEST_WORK_DIR=str(shared), ONETIPS_TEST_QUERY_CAPTURE=str(capture)
        )
        result = run(str(python), str(ROOT / "tests/test_mvp.py"), "-k", "query", "-v", cwd=work, env=trial)
        print(f"{mode} wheel AC-6:\n{result.stderr.decode('utf-8')}", flush=True)
        transcripts.append(capture.read_bytes().splitlines())
    left, right = transcripts
    require(left and len(left) == len(right), "wheel transcript lengths differ or are empty")
    for expected, actual in zip(left, right, strict=True):
        require(expected == actual, f"query output bytes differ:\npure {json.loads(expected)!r}\nnative {json.loads(actual)!r}")
    print(f"AC-9: {len(left)} query exit/stdout/stderr observations are byte-identical.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--build-wheels", action="store_true", help="build, install and compare both wheel variants")
    modes.add_argument("--pure", type=Path, help="compare an already installed pure-wheel interpreter")
    parser.add_argument("--native", type=Path, help="compare an already installed native-wheel interpreter")
    parser.add_argument("--remote-source", help="also install an existing published <owner>/<repo>@<tag> fixture")
    args = parser.parse_args()
    if bool(args.pure) != bool(args.native):
        parser.error("--pure and --native must be specified together")
    if args.remote_source and (args.build_wheels or args.pure):
        parser.error("--remote-source is only for installer acceptance")

    with tempfile.TemporaryDirectory(prefix="OneTips acceptance ") as temp:
        work = Path(temp).resolve()
        if args.build_wheels:
            env = env_for_children()
            parity(work, build_wheel(work, "pure", env), build_wheel(work, "native", env))
        elif args.pure:
            parity(work, args.pure.absolute(), args.native.absolute())
        else:
            installers(work, args.remote_source)


if __name__ == "__main__":
    main()
