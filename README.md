# ai-safe-context

> **Safely pack your repo into LLM-ready Markdown without accidentally leaking secrets.**

`ai-safe-context` is a local-first CLI for developers who paste code into ChatGPT, Claude, Gemini, Cursor, Copilot Chat, or other AI assistants. It scans a repository, respects `.gitignore`, skips noisy/binary/large files, redacts common secrets, and generates a clean `context.md` file you can review before sharing.

## Why this project

Developers increasingly ask AI assistants to debug, review, or explain real projects. The risky part is not the AI conversation — it is accidentally pasting `.env`, API keys, private tokens, internal URLs, or huge dependency folders.

This tool helps reduce that risk with a simple local workflow:

```bash
ai-safe-context ./my-project --output context.md
```

Example output:

```text
Generated my-project/context.md
Scanned 128 files | Included 42 | Skipped 80 | Redacted 6
Review redactions before sharing. ai-safe-context reduces risk but cannot guarantee 100% safety.
```

## Features

- **Local-first**: no account, no cloud upload, no LLM API required.
- **LLM-ready Markdown**: file tree, summaries, and fenced code blocks.
- **Secret redaction**: API keys, bearer tokens, private keys, AWS keys, GitHub tokens, and common `*_SECRET` / `*_TOKEN` patterns.
- **Noise reduction**: skips `.git`, `node_modules`, virtualenvs, caches, lock files, binary files, and oversized files.
- **`.gitignore` aware**: supports common root `.gitignore` file and directory patterns.
- **CLI-friendly**: works in local projects, CI, and future editor integrations.

## Install

Development install from this repository:

```bash
python -m pip install -e .
```

Future package target:

```bash
pipx install ai-safe-context
# or
uvx ai-safe-context
```

## Usage

```bash
# Pack current directory into context.md
ai-safe-context

# Pack another repository
ai-safe-context ../my-app --output my-app-context.md

# Limit file size
ai-safe-context --max-file-size 50000

# Include only source files
ai-safe-context --include "src/**/*.py" --include "tests/**/*.py"

# Exclude additional paths
ai-safe-context --exclude "docs/archive/**"

# Write a machine-readable summary for CI or automation
ai-safe-context --json-summary summary.json

# Write a Markdown risk report before sharing generated context
ai-safe-context --risk-report risk.md
```

## Project config

Add `.ai-safe-context.yml` to a repository to make repeatable context packs easier for a team or CI job:

```yaml
max_file_size: 75000
include:
  - "src/**/*.py"
  - "tests/**/*.py"
exclude:
  - "src/private.py"
respect_gitignore: true
```

For safety, project config cannot disable `.gitignore` handling. Use the explicit `--no-gitignore` CLI flag only for a trusted one-off local run.

CLI flags override config values, so one-off runs can still narrow or expand the generated context.

## Positioning

`ai-safe-context` is not a full secret scanner and does not claim 100% safety. It is a practical context packer that helps developers reduce accidental leakage before asking AI assistants for help.

Useful comparisons:

- **gitleaks**: deep secret scanning for repositories. `ai-safe-context` focuses on generating AI-shareable context.
- **repomix / gitingest**: repo-to-context packing. `ai-safe-context` emphasizes safe defaults and redaction-first output.
- **LLM coding agents**: consume project context. `ai-safe-context` prepares reviewable context before sharing.

See [`docs/COMPARISON.md`](docs/COMPARISON.md) for more detail.

## MVP roadmap

- [x] Local CLI
- [x] Markdown context generation
- [x] `.gitignore` support
- [x] Secret redaction patterns
- [x] File size and binary skipping
- [x] JSON output for automation
- [x] Markdown risk report for sharing review
- [ ] Token counting
- [ ] More precise `.gitignore` semantics
- [ ] GitHub Action preflight check
- [ ] VS Code extension

## Development

```bash
python -m pip install -e .[dev]
python -m pytest -q
python -m ruff check .
```

## Safety note

Always review generated `context.md` before sharing. Secret detection is best-effort and can miss unusual formats or business-sensitive data.

## License

MIT
