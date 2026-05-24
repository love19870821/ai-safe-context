from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".venv",
    "venv",
}

DEFAULT_EXCLUDE_FILES = {
    ".DS_Store",
    ".gitignore",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "OPENAI_API_KEY",
        re.compile(r"(?i)(OPENAI_API_KEY\s*=\s*)(['\"]?)[A-Za-z0-9_\-]{12,}(['\"]?)"),
    ),
    (
        "API_KEY",
        re.compile(r"(?i)([A-Z0-9_]*(?:API|SECRET|TOKEN|PASSWORD|KEY)[A-Z0-9_]*\s*=\s*)(['\"]?)(?!\[REDACTED:)[^\s'\"\[]{8,}(['\"]?)"),
    ),
    (
        "BEARER_TOKEN",
        re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._\-]{12,}"),
    ),
    (
        "PRIVATE_KEY",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
    (
        "AWS_ACCESS_KEY_ID",
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    (
        "GITHUB_TOKEN",
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    ),
]


@dataclass(frozen=True)
class PackOptions:
    output_name: str = "context.md"
    max_file_size: int = 100_000
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    respect_gitignore: bool = True


@dataclass(frozen=True)
class PackSummary:
    scanned_files: int
    included_files: int
    skipped_files: int
    redactions: int


@dataclass(frozen=True)
class PackResult:
    markdown: str
    summary: PackSummary


def pack_repository(root: Path | str, options: PackOptions | None = None) -> PackResult:
    """Pack a repository into redacted, LLM-ready Markdown."""
    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {root_path}")

    opts = options or PackOptions()
    gitignore_patterns = _read_gitignore(root_path) if opts.respect_gitignore else []

    entries: list[tuple[str, str]] = []
    scanned = included = skipped = redactions = 0

    for path in sorted(_iter_files(root_path), key=lambda p: p.relative_to(root_path).as_posix()):
        scanned += 1
        rel = path.relative_to(root_path).as_posix()
        if _should_skip(path, rel, root_path, opts, gitignore_patterns):
            skipped += 1
            continue

        try:
            raw = path.read_bytes()
        except OSError:
            skipped += 1
            continue

        if len(raw) > opts.max_file_size or _looks_binary(raw):
            skipped += 1
            continue

        text = raw.decode("utf-8", errors="replace")
        redacted_text, count = redact_secrets(text)
        redactions += count
        entries.append((rel, redacted_text.rstrip()))
        included += 1

    markdown = _render_markdown(root_path.name, entries, PackSummary(scanned, included, skipped, redactions))
    return PackResult(markdown=markdown, summary=PackSummary(scanned, included, skipped, redactions))


def redact_secrets(text: str) -> tuple[str, int]:
    redactions = 0
    redacted = text
    for label, pattern in SECRET_PATTERNS:
        def repl(match: re.Match[str]) -> str:
            nonlocal redactions
            redactions += 1
            if label in {"OPENAI_API_KEY", "API_KEY"} and len(match.groups()) >= 1:
                prefix = match.group(1)
                quote1 = match.group(2) if len(match.groups()) >= 2 else ""
                quote2 = match.group(3) if len(match.groups()) >= 3 else ""
                return f"{prefix}{quote1}[REDACTED:{label}]{quote2}"
            if label == "BEARER_TOKEN":
                return f"{match.group(1)}[REDACTED:{label}]"
            return f"[REDACTED:{label}]"

        redacted = pattern.sub(repl, redacted)
    return redacted, redactions


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_file():
            yield path


def _read_gitignore(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def _should_skip(
    path: Path,
    rel: str,
    root: Path,
    options: PackOptions,
    gitignore_patterns: list[str],
) -> bool:
    parts = set(path.relative_to(root).parts)
    if parts & DEFAULT_EXCLUDE_DIRS:
        return True
    if path.name in DEFAULT_EXCLUDE_FILES:
        return True
    if path.name == options.output_name:
        return True
    if options.include and not any(fnmatch.fnmatch(rel, pat) for pat in options.include):
        return True
    if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(path.name, pat) for pat in options.exclude):
        return True
    if _matches_gitignore(rel, path.name, gitignore_patterns):
        return True
    return False


def _matches_gitignore(rel: str, name: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            directory = pattern.rstrip("/")
            if rel == directory or rel.startswith(f"{directory}/"):
                return True
            continue
        normalized = pattern.rstrip("/")
        if fnmatch.fnmatch(rel, normalized) or fnmatch.fnmatch(name, normalized):
            return True
        if "/" not in normalized and fnmatch.fnmatch(name, normalized):
            return True
    return False


def _looks_binary(raw: bytes) -> bool:
    if b"\0" in raw:
        return True
    sample = raw[:1024]
    if not sample:
        return False
    text_bytes = bytes(range(32, 127)) + b"\n\r\t\b"
    non_text = sum(byte not in text_bytes for byte in sample)
    return non_text / len(sample) > 0.30


def _render_markdown(repo_name: str, entries: list[tuple[str, str]], summary: PackSummary) -> str:
    tree = "\n".join(f"- `{path}`" for path, _ in entries) or "- No files included"
    sections = [
        f"# AI Safe Context: {repo_name}",
        "",
        "> Generated locally by ai-safe-context. Review before sharing with an AI assistant.",
        "",
        "## Summary",
        "",
        f"- Scanned files: {summary.scanned_files}",
        f"- Included files: {summary.included_files}",
        f"- Skipped files: {summary.skipped_files}",
        f"- Secret redactions: {summary.redactions}",
        "",
        "## Included File Tree",
        "",
        tree,
        "",
        "## Files",
        "",
    ]
    for path, text in entries:
        lang = _language_hint(path)
        sections.extend([f"### `{path}`", "", f"```{lang}", text, "```", ""])
    return "\n".join(sections).rstrip() + "\n"


def _language_hint(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "tsx",
        "jsx": "jsx",
        "md": "markdown",
        "json": "json",
        "toml": "toml",
        "yaml": "yaml",
        "yml": "yaml",
        "sh": "bash",
    }.get(suffix, "")
