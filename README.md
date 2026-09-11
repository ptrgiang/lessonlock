# lessonlock

**Correct it once. Block it forever.**

`lessonlock` turns explicit corrections you give a coding agent into deterministic, reviewable guardrails — then generates a regression probe proving the mistake is blocked.

Works with **Claude Code** and **OpenAI Codex** using one shared guard format and runtime.

```text
Human correction → executable guard → regression probe → proof
```

No model call at enforcement time. No server. No database. Guards live in Git.

## The 30-second demo

```bash
pip install -e .
lessonlock init
lessonlock learn 'Never edit `migrations/generated/**` again.' --id no-generated-migrations
lessonlock install all
lessonlock probe no-generated-migrations
```

Output:

```text
Found correction:
  'Never edit `migrations/generated/**` again.'

Can this be enforced mechanically?  YES
Guard       protected_path
✓ Created .lessonlock/guards/no-generated-migrations.yml

LESSONLOCK PROBE
Rule                  no-generated-migrations
Known bad action      Edit migrations/generated/example.txt
Expected              BLOCK
Actual                DENY
✓ Guard works
```

Later, if Claude Code uses `Edit`/`Write` or Codex uses `apply_patch` against that path, its `PreToolUse` call is denied before the edit executes.

## Why this exists

Coding agents can remember a rule and still violate it later. A correction such as “never touch generated migrations” should not remain advice; when the intent is mechanically enforceable, it should become a barrier.

`lessonlock` is intentionally narrower than a policy platform. It starts from a real human correction, compiles only the part that can be enforced deterministically, and attaches a probe.

## V0.1 guard types

| Correction pattern | Guard | What happens |
|---|---|---|
| `Never edit \`path/**\`` | `protected_path` | Blocks Claude `Edit`/`Write` and Codex `apply_patch` |
| `Never run \`command\`` | `command_deny` | Blocks matching shell commands |
| `Use \`uv pip\` instead of \`pip\`` | `command_rewrite` | Rewrites the shell tool input |
| `Never commit directly to branch \`main\`` | `branch_guard` | Blocks commit/push on protected branches |
| `Before commit, run \`pytest -q\` after changing \`src/**\`` | `verify_before_commit` | Runs verification and blocks commit on failure |

Vague corrections are **not** silently turned into fake policy:

```bash
$ lessonlock learn 'Write cleaner code next time.'
Can this be enforced mechanically?  NO
Reason: Correction is advisory or ambiguous. Put enforceable paths/commands/branches in backticks.
```

That refusal is a feature: enforcement should be explainable.

## Commands

```text
lessonlock init
lessonlock learn CORRECTION [--id ID] [--force]
lessonlock list
lessonlock why GUARD_ID
lessonlock probe GUARD_ID
lessonlock probe --all
lessonlock install claude
lessonlock install codex
lessonlock install all
```

`lessonlock why` is the scar receipt: it shows the human correction and when the guard was learned.

## Guard files are boring on purpose

```yaml
version: 1
id: no-prod-curl
kind: command_deny
enabled: true
patterns:
  - curl\\ https://prod\\.example\\.com
message: "This mistake was already corrected once: Never run `curl https://prod.example.com`."
source:
  type: correction
  text: "Never run `curl https://prod.example.com`."
  learned_at: "2026-09-12T00:00:00+00:00"
```

They are plain YAML so teams can review them like code.

## Agent adapters

### Claude Code

```bash
lessonlock install claude
```

This merges a project-level `PreToolUse` hook into `.claude/settings.json` and listens to `Bash|PowerShell|Edit|Write`, including Windows-native PowerShell sessions.

### OpenAI Codex

```bash
lessonlock install codex
```

This merges a project-level `PreToolUse` hook into `.codex/hooks.json`. Codex exposes shell calls as `Bash` and native file edits as `apply_patch`; lessonlock parses the patch targets before allowing the tool call.

Codex may ask you to review/trust a newly added project hook on startup. That trust step is intentionally not bypassed by lessonlock.

### Both

```bash
lessonlock install all
```

Claude Code and Codex use the same `.lessonlock/guards/*.yml` files, so a correction becomes one portable project policy instead of two agent-specific rules.

The runtime emits the structured `PreToolUse` decision format understood by both adapters. A denied action is blocked before execution; a rewrite returns the complete updated tool input.

## Design rules

- deterministic runtime; no LLM required to enforce a guard
- one correction, one guard format across supported agents
- default to advisory when a correction cannot be compiled safely
- one guard = one reviewable file
- every supported guard kind must have a probe
- project-local by default
- never silently bypass an agent's hook-trust mechanism
- fail small: lessonlock should not become another agent framework

## Roadmap

- **v0.1** — Claude Code + Codex, 5 guard kinds, `learn/list/why/probe`
- **v0.2** — detect explicit corrections from agent transcripts (`learn --last`)
- **v0.3** — Gemini CLI / OpenCode adapters
- **v0.4** — richer shell-write/path enforcement and hook diagnostics
- **v0.5** — team lesson sharing and richer Git review metadata
- **v0.6** — repeated-correction suggestions
- **v0.7** — prevented-mistake metrics

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
pytest
python -m build
```

CI intentionally runs on pull requests and manual dispatch, not every push to `main`, to keep the PR-first workflow useful and reduce noisy failure emails.

## Status

Alpha. The core file/command/branch enforcement path is intentionally small enough to audit. Test it in a non-critical repository before relying on it for important workflows.

## License

MIT
