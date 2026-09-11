from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re


@dataclass(frozen=True)
class CompileResult:
    enforceable: bool
    guard: dict | None
    reason: str


def _quoted(text: str) -> list[str]:
    values = re.findall(r"`([^`]+)`|\"([^\"]+)\"|'([^']+)'", text)
    return [next(part for part in group if part) for group in values]


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:48] or "lesson"


def _base(kind: str, correction: str, guard_id: str | None) -> dict:
    return {
        "version": 1,
        "id": guard_id or _slug(correction),
        "kind": kind,
        "enabled": True,
        "message": f"This mistake was already corrected once: {correction}",
        "source": {
            "type": "correction",
            "text": correction,
            "learned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }


def compile_correction(correction: str, guard_id: str | None = None) -> CompileResult:
    text = correction.strip()
    lower = text.lower()
    quoted = _quoted(text)

    if re.search(r"\b(never|do not|don't|dont)\b.*\b(edit|write|modify|touch)\b", lower) and quoted:
        guard = _base("protected_path", text, guard_id)
        guard["paths"] = [quoted[0]]
        return CompileResult(True, guard, "protected path")

    if re.search(r"\b(never|do not|don't|dont)\b.*\b(run|execute)\b", lower) and quoted:
        guard = _base("command_deny", text, guard_id)
        guard["patterns"] = [re.escape(quoted[0])]
        return CompileResult(True, guard, "denied command")

    if re.search(r"\buse\b.*\binstead of\b", lower) and len(quoted) >= 2:
        guard = _base("command_rewrite", text, guard_id)
        guard["pattern"] = re.escape(quoted[1])
        guard["replacement"] = quoted[0]
        return CompileResult(True, guard, "command rewrite")

    if re.search(r"\b(never|do not|don't|dont)\b.*\b(commit|push)\b.*\b(branch|to)\b", lower) and quoted:
        guard = _base("branch_guard", text, guard_id)
        guard["branches"] = [quoted[0]]
        guard["command_patterns"] = [r"\bgit\s+commit\b", r"\bgit\s+push\b"]
        return CompileResult(True, guard, "protected branch")

    if re.search(r"\b(before|prior to)\b.*\bcommit\b", lower) and len(quoted) >= 2:
        guard = _base("verify_before_commit", text, guard_id)
        guard["check"] = {"command": quoted[0], "timeout": 120}
        guard["changed_paths"] = [quoted[1]]
        return CompileResult(True, guard, "verification before commit")

    return CompileResult(
        False,
        None,
        "Correction is advisory or ambiguous. Put enforceable paths/commands/branches in backticks.",
    )
