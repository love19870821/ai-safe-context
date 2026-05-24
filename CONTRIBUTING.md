# Contributing to ai-safe-context

Thanks for helping make AI-assisted development safer.

## Good first contributions

- Add redaction patterns with tests.
- Improve Markdown rendering.
- Improve `.gitignore` compatibility.
- Add examples for real-world project types.
- Improve Windows/macOS/Linux behavior.

## Development setup

```bash
python -m pip install -e .[dev]
python -m pytest -q
python -m ruff check .
```

## Redaction rule policy

Every new redaction rule must include:

1. A test showing the secret is removed.
2. A test or example showing useful surrounding text is preserved.
3. A clear label, e.g. `[REDACTED:GITHUB_TOKEN]`.

Do not claim perfect security. This project reduces accidental leakage; it does not replace dedicated security review.
