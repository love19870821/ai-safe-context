# Security Policy

## Reporting a vulnerability

Please do not open a public issue for suspected vulnerabilities or bypasses that expose real secrets.

For now, create a private report with:

- A minimal reproduction.
- The input text or synthetic secret pattern.
- The expected redaction behavior.
- Your operating system and Python version.

## Scope

`ai-safe-context` provides best-effort reduction of accidental leakage. It is not a guarantee that all sensitive information is removed.

Sensitive business data, internal URLs, customer data, credentials in unusual formats, and secrets embedded in binary or encoded data may still require manual review.
