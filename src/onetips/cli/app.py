from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from onetips.cli.output import report, write_stdout
from onetips.cli.parser import build_parser
from onetips.commands import check, index, snippets, verify
from onetips.commands.find import find
from onetips.commands.result import CommandResult
from onetips.commands.show import show
from onetips.core.diagnostic import Diagnostic
from onetips.core.errors import ConfigError, DataError, UsageError
from onetips.scaffold import init_project, new_tip


def _validate_show(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not (args.metadata or args.section or args.code):
        parser.error("show requires --metadata, --section, or --code")
    if args.metadata and (args.section or args.code):
        parser.error("--metadata cannot be combined with --section or --code")
    if (args.lang is not None or args.status is not None) and not args.code:
        parser.error("--lang and --status require --code")
    if args.json and not (args.metadata or args.code):
        parser.error("--json requires --metadata or --code")


def _query(args: argparse.Namespace) -> int:
    try:
        if args.command == "find":
            text = find(args.skill_dir, args.id, args.category, args.tag, args.keyword, args.json)
        else:
            text = show(
                args.skill_dir,
                args.id,
                metadata=args.metadata,
                section=args.section,
                code=args.code,
                lang=args.lang,
                status=args.status,
                as_json=args.json,
            )
        write_stdout(text)
    except (DataError, OSError, UnicodeError) as exc:
        print(f"onetips: {exc}", file=sys.stderr)
        return 1
    return 0


def _finish(result: CommandResult, *, always_report: bool = True) -> int:
    write_stdout(result.output)
    return report(result.diagnostics) if always_report or result.diagnostics else 0


def _author(args: argparse.Namespace) -> int:
    root = Path.cwd()
    try:
        if args.command == "index":
            return _finish(index.run(root, check=args.check))
        if args.command == "check":
            return _finish(check.run(root))
        return _finish(snippets.run(root, args.id))
    except ConfigError as exc:
        report([Diagnostic(exc.path, 1, "E-CONFIG", str(exc))])
        return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    if command == "show":
        _validate_show(parser, args)
    if command in ("show", "find"):
        return _query(args)
    try:
        if command == "init":
            print(f"Initialized {init_project(args.dir, args.name)}")
        elif command == "new":
            print(f"Created {new_tip(Path.cwd(), args.id, args.category)}")
        elif command in ("index", "check", "snippets"):
            return _author(args)
        elif command == "verify":
            return _finish(verify.run(args.skill_dir), always_report=False)
        else:
            parser.print_help()
    except (UsageError, OSError) as exc:
        print(f"onetips: {exc}", file=sys.stderr)
        return 2
    return 0
