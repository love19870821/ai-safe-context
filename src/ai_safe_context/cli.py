from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .core import PackSummary, load_options_from_config, pack_repository


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
        default=None,
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
    parser.add_argument(
        "--risk-report",
        help="Write a Markdown risk report with sharing guidance to this path.",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.path)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    options = load_options_from_config(
        root,
        output_name=output.name,
        max_file_size=args.max_file_size,
        include=tuple(args.include) if args.include else None,
        exclude=tuple(args.exclude) if args.exclude else None,
        respect_gitignore=False if args.no_gitignore else None,
    )
    result = pack_repository(root, options)
    output.write_text(result.markdown, encoding="utf-8")

    summary = result.summary
    if args.json_summary:
        json_summary = _resolve_output_path(root, args.json_summary)
        json_summary.write_text(
            json.dumps(
                {
                    "output": str(output),
                    "risk_level": _risk_level(summary),
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
    if args.risk_report:
        risk_report = _resolve_output_path(root, args.risk_report)
        risk_report.write_text(_render_risk_report(summary, output), encoding="utf-8")
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


def _resolve_output_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _risk_level(summary: PackSummary) -> str:
    if summary.redactions:
        return "review-required"
    if summary.skipped_files:
        return "low-with-skipped-files"
    return "low"


def _render_risk_report(summary: PackSummary, output: Path) -> str:
    level = _risk_level(summary)
    checks = [
        "Review the generated Markdown before sharing it with any AI system.",
        "Confirm skipped files are intentionally excluded.",
        "Do not treat automated redaction as a guarantee of safety.",
    ]
    if summary.redactions:
        checks.insert(0, "Inspect every `[REDACTED:*]` marker and nearby context.")
    return (
        "# ai-safe-context Risk Report\n\n"
        f"- Output: `{output}`\n"
        f"- Risk level: `{level}`\n"
        f"- Scanned files: {summary.scanned_files}\n"
        f"- Included files: {summary.included_files}\n"
        f"- Skipped files: {summary.skipped_files}\n"
        f"- Secret redactions: {summary.redactions}\n\n"
        "## Recommended checks\n\n"
        + "".join(f"- {check}\n" for check in checks)
    )


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
