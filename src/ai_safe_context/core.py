from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

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


def load_options_from_config(
    root: Path | str,
    *,
    output_name: str = "context.md",
    max_file_size: int | None = None,
    include: tuple[str, ...] | None = None,
    exclude: tuple[str, ...] | None = None,
    respect_gitignore: bool | None = None,
) -> PackOptions:
    """Load pack options from a small project config file and CLI overrides.

    Supported config filenames: `.ai-safe-context.yml`, `.ai-safe-context.yaml`,
    and `.ai-safe-context.json`. YAML support intentionally handles only the
    simple scalar/list shape used by this tool so the package remains dependency-free.
    """
    root_path = Path(root).resolve()
    options = PackOptions(output_name=output_name)
    config_path = _find_config_file(root_path)
    if config_path:
        options = _options_from_config_data(_read_config(config_path), output_name=output_name)
    if max_file_size is not None:
        options = replace(options, max_file_size=max_file_size)
    if include is not None:
        options = replace(options, include=include)
    if exclude is not None:
        options = replace(options, exclude=exclude)
    if respect_gitignore is not None:
        options = replace(options, respect_gitignore=respect_gitignore)
    return options


def pack_repository(root: Path | str, options: PackOptions | None = None) -> PackResult:
    """Pack a repository into redacted, LLM-ready Markdown."""
    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {root_path}")

    opts = options or load_options_from_config(root_path)
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


def _find_config_file(root: Path) -> Path | None:
    for name in (".ai-safe-context.yml", ".ai-safe-context.yaml", ".ai-safe-context.json"):
        path = root / name
        if path.is_file():
            return path
    return None


def _read_config(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        import json

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Config must be an object: {path}")
        return data
    return _parse_simple_yaml(raw)


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("-"):
            if current_list_key is None:
                raise ValueError("YAML list item found before a list key")
            data.setdefault(current_list_key, []).append(_parse_scalar(stripped[1:].strip()))
            continue
        if ":" not in stripped:
            raise ValueError(f"Unsupported config line: {line}")
        key, value = stripped.split(":", 1)
        key = key.strip().replace("-", "_")
        value = value.strip()
        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = _parse_scalar(value)
            current_list_key = None
    return data


def _parse_scalar(value: str) -> Any:
    unquoted = value.strip().strip("'").strip('"')
    lowered = unquoted.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    try:
        return int(unquoted)
    except ValueError:
        return unquoted


def _options_from_config_data(data: dict[str, Any], *, output_name: str) -> PackOptions:
    allowed = {"max_file_size", "include", "exclude", "respect_gitignore"}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"Unknown ai-safe-context config key(s): {', '.join(unknown)}")
    return PackOptions(
        output_name=output_name,
        max_file_size=_coerce_int(data.get("max_file_size", PackOptions.max_file_size), "max_file_size"),
        include=_coerce_str_tuple(data.get("include", ()), "include"),
        exclude=_coerce_str_tuple(data.get("exclude", ()), "exclude"),
        respect_gitignore=PackOptions.respect_gitignore,
    )


def _coerce_int(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _coerce_bool(value: Any, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "yes", "on"}:
            return True
        if lowered in {"false", "no", "off"}:
            return False
    raise ValueError(f"{key} must be a boolean")


def _coerce_str_tuple(value: Any, key: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        if not all(isinstance(item, str) for item in value):
            raise ValueError(f"{key} must contain only strings")
        return tuple(value)
    raise ValueError(f"{key} must be a string or list of strings")


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
    if options.include and not any(_matches_pattern(rel, path.name, pat) for pat in options.include):
        return True
    if any(_matches_pattern(rel, path.name, pat) for pat in options.exclude):
        return True
    if _matches_gitignore(rel, path.name, gitignore_patterns):
        return True
    return False


def _matches_pattern(rel: str, name: str, pattern: str) -> bool:
    normalized = pattern.strip().lstrip("/")
    variants = {normalized}
    if "**/" in normalized:
        variants.add(normalized.replace("**/", ""))
    return any(fnmatch.fnmatch(rel, variant) or fnmatch.fnmatch(name, variant) for variant in variants)


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
