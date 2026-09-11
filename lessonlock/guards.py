from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import fnmatch
import re
import subprocess

import yaml


@dataclass(frozen=True)
class Decision:
    action: str  # allow | deny | rewrite
    reason: str = ""
    updated_input: dict[str, Any] | None = None
    guard_id: str | None = None


def load_guards(root: Path) -> list[dict[str, Any]]:
    guard_dir = root / ".lessonlock" / "guards"
    if not guard_dir.exists():
        return []
    guards: list[dict[str, Any]] = []
    for path in sorted(guard_dir.glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict) and data.get("enabled", True):
            data["_path"] = str(path)
            guards.append(data)
    return guards


def dump_guard(guard: dict[str, Any]) -> str:
    clean = {k: v for k, v in guard.items() if not k.startswith("_")}
    return yaml.safe_dump(clean, sort_keys=False, allow_unicode=True)


def _matches_any(value: str, patterns: Iterable[str]) -> bool:
    value = value.replace("\\", "/")
    return any(fnmatch.fnmatch(value, p.replace("\\", "/")) for p in patterns)


def _path_matches(file_path: str, patterns: Iterable[str], cwd: Path) -> bool:
    normalized = file_path.replace("\\", "/")
    candidates = [normalized]
    try:
        relative = Path(file_path).resolve().relative_to(cwd.resolve())
        candidates.append(relative.as_posix())
    except (ValueError, OSError):
        pass
    return any(_matches_any(candidate, patterns) for candidate in candidates)


def _regex_any(value: str, patterns: Iterable[str]) -> bool:
    return any(re.search(p, value, re.IGNORECASE) for p in patterns)


def _current_branch(cwd: Path) -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return proc.stdout.strip()


def _staged_files(cwd: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _run_check(command: str, cwd: Path, timeout: int) -> tuple[bool, str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, output[-2000:]


def evaluate_guard(
    guard: dict[str, Any],
    event: dict[str, Any],
    cwd: Path,
    *,
    get_branch=_current_branch,
    get_staged_files=_staged_files,
    run_check=_run_check,
) -> Decision | None:
    kind = guard.get("kind")
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    guard_id = guard.get("id", "unnamed")
    message = guard.get("message") or f"Blocked by lessonlock guard '{guard_id}'."

    if kind == "protected_path":
        if tool not in {"Edit", "Write"}:
            return None
        file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        patterns = guard.get("paths", [])
        if file_path and _path_matches(file_path, patterns, cwd):
            return Decision("deny", message, guard_id=guard_id)

    elif kind == "command_deny":
        if tool not in {"Bash", "PowerShell"}:
            return None
        command = str(tool_input.get("command") or "")
        if _regex_any(command, guard.get("patterns", [])):
            return Decision("deny", message, guard_id=guard_id)

    elif kind == "command_rewrite":
        if tool not in {"Bash", "PowerShell"}:
            return None
        command = str(tool_input.get("command") or "")
        pattern = guard.get("pattern", "")
        replacement = guard.get("replacement", "")
        if pattern and re.search(pattern, command):
            updated = dict(tool_input)
            updated["command"] = re.sub(pattern, replacement, command)
            return Decision("rewrite", message, updated, guard_id)

    elif kind == "branch_guard":
        if tool not in {"Bash", "PowerShell"}:
            return None
        command = str(tool_input.get("command") or "")
        triggers = guard.get("command_patterns", [r"\bgit\s+commit\b", r"\bgit\s+push\b"])
        if not _regex_any(command, triggers):
            return None
        branch = get_branch(cwd)
        if branch and _matches_any(branch, guard.get("branches", [])):
            return Decision("deny", message, guard_id=guard_id)

    elif kind == "verify_before_commit":
        if tool not in {"Bash", "PowerShell"}:
            return None
        command = str(tool_input.get("command") or "")
        if not re.search(r"\bgit\s+commit\b", command):
            return None
        staged = get_staged_files(cwd)
        changed_patterns = guard.get("changed_paths", ["**"])
        if staged and not any(_matches_any(path, changed_patterns) for path in staged):
            return None
        check = guard.get("check") or {}
        check_command = str(check.get("command") or "")
        if not check_command:
            return Decision("deny", f"{message} Missing check.command.", guard_id=guard_id)
        ok, output = run_check(check_command, cwd, int(check.get("timeout", 120)))
        if not ok:
            detail = f"\n\nVerification failed: `{check_command}`"
            if output:
                detail += f"\n{output}"
            return Decision("deny", message + detail, guard_id=guard_id)

    return None


def evaluate_all(guards: Iterable[dict[str, Any]], event: dict[str, Any], cwd: Path) -> Decision:
    rewrite: Decision | None = None
    current_event = event
    for guard in guards:
        decision = evaluate_guard(guard, current_event, cwd)
        if decision is None:
            continue
        if decision.action == "deny":
            return decision
        if decision.action == "rewrite":
            rewrite = decision
            current_event = dict(current_event)
            current_event["tool_input"] = decision.updated_input or current_event.get("tool_input", {})
    return rewrite or Decision("allow")
