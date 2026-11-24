"""Measure installed wheel startup and in-process catalog queries."""

import argparse
import json
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "fixtures/minimal/skills/acme-tips/INDEX.md"
COLD_RUNS = 10
QUERY_RUNS = 30
SYNTHETIC_ROWS = 10_000

CORE_MODULES = (
    "onetips.core.index",
    "onetips.core.section",
    "onetips.core.config",
    "onetips.core.rules.metadata",
    "onetips.core.rules.body",
)
LOADER_SCRIPT = """
import importlib
import json
import sys

print(json.dumps({name: type(importlib.import_module(name).__loader__).__name__ for name in sys.argv[1:]}))
"""
QUERY_SCRIPT = """
import statistics
import sys
import time
from pathlib import Path

from onetips.core.index import find_rows, parse_catalog

fixture, runs, size = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
minimal = fixture.read_text(encoding='utf-8')
header = minimal[:minimal.index('|[idempotency-keys](')].replace('2 tips.', f'{size} tips.', 1)
synthetic = header + ''.join(
    f'|[tip-{n:05d}](references/tip-{n:05d}.md)|Topic {n:05d}|Synthetic Example SDK topic.|'
    f'{"retry" if n % 100 == 0 else "other"}|example-sdk &gt;=1|tested 0, compiled 0, unverified 0|\\n'
    for n in range(size)
)
for label, text, case, count, expected in (
    ('fixture', minimal, 'transient', 2, 1), ('synthetic', synthetic, 'example sdk', size, (size + 99) // 100),
):
    timings = []
    for _ in range(runs):
        start = time.perf_counter_ns()
        catalog = parse_catalog(text)
        result = find_rows(catalog, None, 'networking', 'retry', case)
        elapsed = time.perf_counter_ns() - start
        if len(catalog.rows) != count or len(result) != expected:
            raise RuntimeError(f'{label}: expected {count} rows, {expected} matches; got {len(catalog.rows)}, {len(result)}')
        timings.append(elapsed)
    print(label, statistics.median(timings) / 1_000_000)
"""


def run(python: Path, *args: str, cwd: Path) -> bytes:
    result = subprocess.run(
        [str(python), "-I", *args],
        cwd=cwd,
        env=dict(os.environ, PYTHONUTF8="1"),
        check=False,
        capture_output=True,
        timeout=90,
    )
    if result.returncode or result.stderr:
        raise RuntimeError(
            f"{python} {args[:1]}: exit {result.returncode}\n"
            f"{result.stdout.decode(errors='replace')}{result.stderr.decode(errors='replace')}"
        )
    return result.stdout


def validate_loader(python: Path, label: str, want: str, work: Path) -> None:
    loaders = json.loads(run(python, "-c", LOADER_SCRIPT, *CORE_MODULES, cwd=work))
    expected = dict.fromkeys(CORE_MODULES, want)
    if loaders != expected:
        raise RuntimeError(f"{label} wheel ({python}): expected {expected!r}, got {loaders!r}")
    print(f"{label} core modules: {want}", flush=True)


def measure(python: Path, label: str, work: Path) -> None:
    startup = []
    for _ in range(COLD_RUNS):
        start = time.perf_counter_ns()
        output = run(python, "-m", "onetips", "--help", cwd=work)
        startup.append(time.perf_counter_ns() - start)
        if b"usage: onetips" not in output or b"find" not in output:
            raise RuntimeError(f"{label}: unexpected OneTips help: {output!r}")
    output = run(python, "-c", QUERY_SCRIPT, str(INDEX), str(QUERY_RUNS), str(SYNTHETIC_ROWS), cwd=work)
    queries = dict(line.split() for line in output.decode().splitlines())
    print(
        f"{label}: --help median {statistics.median(startup) / 1_000_000:.3f} ms ({COLD_RUNS} cold processes); "
        f"parse+filter medians {float(queries['fixture']):.3f} ms (fixture), "
        f"{float(queries['synthetic']):.3f} ms ({SYNTHETIC_ROWS:,} rows), each {QUERY_RUNS} iterations.",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pure", type=Path, required=True, help="Python with pure onetips wheel installed")
    parser.add_argument("--native", type=Path, required=True, help="Python with mypyc onetips wheel installed")
    args = parser.parse_args()
    pure, native = args.pure.absolute(), args.native.absolute()
    with tempfile.TemporaryDirectory(prefix="OneTips benchmark ") as directory:
        work = Path(directory)
        validate_loader(pure, "pure", "SourceFileLoader", work)
        validate_loader(native, "native", "ExtensionFileLoader", work)
        measure(pure, "pure", work)
        measure(native, "native", work)


if __name__ == "__main__":
    main()
