from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path

from onetips.core.section import SECTION_KEYS
from onetips.core.snippet import SNIPPET_STATUSES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onetips",
        description="Create, validate, and query OneTips skill projects.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('onetips')}")
    commands = parser.add_subparsers(dest="command")
    init = commands.add_parser("init", help="Initialize a Tips project")
    init.add_argument("dir", type=Path, nargs="?", default=Path())
    init.add_argument("--name", required=True)
    new = commands.add_parser("new", help="Create a draft Tip")
    new.add_argument("id")
    new.add_argument("--category", required=True)
    index = commands.add_parser("index", help="Build the skill topic index")
    index.add_argument("--check", action="store_true", help="Show differences without rewriting")
    commands.add_parser("check", help="Validate a Tips project")
    snippets = commands.add_parser("snippets", help="Run checks for trusted project snippets")
    snippets.add_argument("--id")
    verify = commands.add_parser("verify", help="Verify an installed or source skill")
    verify.add_argument("skill_dir", type=Path)
    find_parser = commands.add_parser("find", help="Find Tips in the skill index")
    find_parser.add_argument("--skill-dir", type=Path, required=True)
    for option in ("id", "category", "tag", "keyword"):
        find_parser.add_argument(f"--{option}")
    find_parser.add_argument("--json", action="store_true")
    show_parser = commands.add_parser("show", help="Select content from an indexed Tip")
    show_parser.add_argument("--skill-dir", type=Path, required=True)
    show_parser.add_argument("id")
    show_parser.add_argument("--metadata", action="store_true")
    show_parser.add_argument("--section", choices=SECTION_KEYS)
    show_parser.add_argument("--code", action="store_true")
    show_parser.add_argument("--lang")
    show_parser.add_argument("--status", choices=SNIPPET_STATUSES)
    show_parser.add_argument("--json", action="store_true")
    return parser
