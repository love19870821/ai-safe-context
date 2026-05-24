# ai-safe-context Implementation Plan

**Goal:** Build a practical open-source CLI that turns a repository into AI-shareable Markdown while reducing accidental secret leakage.

**Architecture:** Pure Python package with a small core library and CLI wrapper. The core scans files, applies ignore rules, redacts sensitive patterns, and renders Markdown. The CLI handles arguments, output path, and user-facing summaries.

**Tech Stack:** Python 3.9+, pytest, ruff, hatchling packaging.

---

## Product decision

GitHub project: **ai-safe-context**.

Positioning:

> Local-first repo context packer for AI assistants, with safe defaults and best-effort secret redaction.

Why this direction:

- Clear daily pain: developers want to send repo context to AI but fear leaking secrets.
- Large audience: any ChatGPT / Claude / Cursor / Gemini / Copilot Chat user.
- Fast MVP: no backend, no login, no model API, no cloud cost.
- GitHub-star friendly: one-command demo, security angle, easy to understand.
- Low maintenance: core file scanning + redaction rules can evolve gradually.

---

## MVP tasks

### Task 1: Core packer

**Objective:** Scan a repository and produce Markdown with included files.

**Files:**
- Create: `src/ai_safe_context/core.py`
- Test: `tests/test_core.py`

**Verification:**

```bash
python -m pytest tests/test_core.py -q
```

Expected: core tests pass.

### Task 2: Safety defaults

**Objective:** Skip ignored, large, binary, dependency, and cache files.

**Files:**
- Modify: `src/ai_safe_context/core.py`
- Test: `tests/test_core.py`

**Verification:**

```bash
python -m pytest tests/test_core.py -q
```

Expected: skipped file counts and output exclusions are correct.

### Task 3: Secret redaction

**Objective:** Redact common API keys, bearer tokens, private keys, AWS keys, GitHub tokens, and generic secret assignments.

**Files:**
- Modify: `src/ai_safe_context/core.py`
- Test: `tests/test_core.py`

**Verification:**

```bash
python -m pytest tests/test_core.py -q
```

Expected: raw secret values do not appear in generated Markdown.

### Task 4: CLI

**Objective:** Provide `ai-safe-context` command with output, include, exclude, max-size, and gitignore options.

**Files:**
- Create: `src/ai_safe_context/cli.py`
- Test: `tests/test_cli.py`
- Modify: `pyproject.toml`

**Verification:**

```bash
python -m pytest tests/test_cli.py -q
python -m ai_safe_context.cli --help
```

Expected: CLI writes `context.md` and prints summary.

### Task 5: GitHub-ready repo polish

**Objective:** Add README, license, contribution guide, changelog, and ignore rules.

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `.gitignore`

**Verification:**

```bash
python -m pytest -q
python -m ruff check .
```

Expected: tests pass; lint clean or documented if ruff is unavailable.
