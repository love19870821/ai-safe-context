# Comparison

`ai-safe-context` sits between repository packers and secret scanners. It is intentionally small: the goal is to create reviewable AI context with safer defaults, not to replace dedicated security tooling.

## gitleaks

**Best for:** deep secret scanning in Git repositories and CI.

**Use gitleaks when:**

- You need a dedicated secret scanner.
- You want CI enforcement for committed credentials.
- You need mature detection rules and reporting.

**Use ai-safe-context when:**

- You want a Markdown bundle to paste into an AI assistant.
- You want noisy files skipped and common secrets redacted before review.
- You want a simple local-first workflow without configuring a full scanner.

## repomix / gitingest-style repository packers

**Best for:** turning a codebase into a prompt-friendly text bundle.

**Use repository packers when:**

- You need broad language support and context packaging features.
- Your main concern is compacting a repo for an LLM.

**Use ai-safe-context when:**

- Your first concern is reducing accidental leakage.
- You want conservative defaults for dependencies, caches, binary files, symlinks, and common secret patterns.
- You want machine-readable summary output for automation.

## Dedicated AI coding agents

**Best for:** autonomous edits, code review, refactoring, and task execution.

**Use an AI coding agent when:**

- You want the tool to inspect and modify a repository directly.
- You are comfortable granting local workspace access to the agent.

**Use ai-safe-context when:**

- You only want to prepare context for a separate AI conversation.
- You want to review the generated context before sharing it.
- You need a lightweight preprocessing step for manual or automated workflows.

## Design principles

- Local-first by default.
- No cloud upload required.
- Best-effort redaction, never a 100% safety guarantee.
- Reviewable output over hidden magic.
- Automation-friendly summaries for CI and editor integrations.
