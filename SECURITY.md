# Security Policy

`lessonlock` runs inside developer workflows and can allow, deny, or rewrite coding-agent tool calls. Treat guard files and hook configuration as executable policy.

## Reporting a vulnerability

Please open a GitHub security advisory or private vulnerability report when available. Avoid publishing working exploits before a fix is available.

Useful reports include:

- the affected lessonlock version or commit
- operating system and Python version
- the guard configuration involved
- the hook input that bypassed or incorrectly triggered a guard
- a minimal reproduction

## Scope

Security-sensitive behavior includes path-matching bypasses, command-matching bypasses, unsafe rewrites, hook installation that corrupts existing settings, and cases where a guard reports `BLOCK` but the protected tool call still executes.

Until lessonlock reaches a stable release, test new guards in a non-critical repository before relying on them for important workflows.
