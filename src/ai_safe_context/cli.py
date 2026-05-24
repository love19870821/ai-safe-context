from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .core import PackOptions, pack_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-safe-context",
        description="Pack a repository into redacted, LLM-ready Markdown context.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository directory to pack")
    parser.add_argument("-o", "--output", default="context.md", help="Output Markdown file")
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=100_000,
        help="Maximum included file size in bytes (default: 100000)",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Glob pattern to include. Can be used multiple times.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob pattern to exclude. Can be used multiple times.",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not read .gitignore patterns.",
    )
    parser.add_argument(
        "--json-summary",
        help="Write a machine-readable JSON summary to this path.",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.path)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    options = PackOptions(
        output_name=output.name,
        max_file_size=args.max_file_size,
        include=tuple(args.include),
        exclude=tuple(args.exclude),
        respect_gitignore=not args.no_gitignore,
    )
    result = pack_repository(root, options)
    output.write_text(result.markdown, encoding="utf-8")

    summary = result.summary
    if args.json_summary:
        json_summary = Path(args.json_summary)
        if not json_summary.is_absolute():
            json_summary = root / json_summary
        json_summary.write_text(
            json.dumps(
                {
                    "output": str(output),
                    "scanned_files": summary.scanned_files,
                    "included_files": summary.included_files,
                    "skipped_files": summary.skipped_files,
                    "redactions": summary.redactions,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"Generated {output}")
    print(
        "Scanned {scanned} files | Included {included} | Skipped {skipped} | Redacted {redactions}".format(
            scanned=summary.scanned_files,
            included=summary.included_files,
            skipped=summary.skipped_files,
            redactions=summary.redactions,
        )
    )
    if summary.redactions:
        print("Review redactions before sharing. ai-safe-context reduces risk but cannot guarantee 100% safety.")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
