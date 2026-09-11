from __future__ import annotations

from pathlib import Path
import re

from .guards import evaluate_guard


def _sample_from_glob(pattern: str) -> str:
    value = pattern.replace("**/", "demo/").replace("/**", "/example.txt").replace("*", "example")
    return value.strip("/") or "example.txt"


def probe_guard(guard: dict, cwd: Path) -> tuple[bool, str, str, str]:
    kind = guard.get("kind")

    if kind == "protected_path":
        sample = _sample_from_glob((guard.get("paths") or ["blocked.txt"])[0])
        event = {"tool_name": "Edit", "tool_input": {"file_path": sample}}
        decision = evaluate_guard(guard, event, cwd)
        actual = decision.action.upper() if decision else "ALLOW"
        return actual == "DENY", f"Edit {sample}", "BLOCK", actual

    if kind == "command_deny":
        pattern = (guard.get("patterns") or ["rm -rf"])[0]
        sample = pattern.replace("\\ ", " ").replace("\\-", "-").replace("\\", "")
        event = {"tool_name": "Bash", "tool_input": {"command": sample}}
        decision = evaluate_guard(guard, event, cwd)
        actual = decision.action.upper() if decision else "ALLOW"
        return actual == "DENY", sample, "BLOCK", actual

    if kind == "command_rewrite":
        pattern = guard.get("pattern", "pip")
        sample = re.sub(r"\\(.)", r"\1", pattern)
        event = {"tool_name": "Bash", "tool_input": {"command": sample + " install demo"}}
        decision = evaluate_guard(guard, event, cwd)
        actual = "REWRITE" if decision and decision.action == "rewrite" else "ALLOW"
        return actual == "REWRITE", event["tool_input"]["command"], "REWRITE", actual

    if kind == "branch_guard":
        branch = (guard.get("branches") or ["main"])[0]
        event = {"tool_name": "Bash", "tool_input": {"command": "git commit -m probe"}}
        decision = evaluate_guard(guard, event, cwd, get_branch=lambda _cwd: branch)
        actual = decision.action.upper() if decision else "ALLOW"
        return actual == "DENY", f"git commit on {branch}", "BLOCK", actual

    if kind == "verify_before_commit":
        changed = (guard.get("changed_paths") or ["src/**"])[0]
        sample_file = _sample_from_glob(changed)
        event = {"tool_name": "Bash", "tool_input": {"command": "git commit -m probe"}}
        decision = evaluate_guard(
            guard,
            event,
            cwd,
            get_staged_files=lambda _cwd: [sample_file],
            run_check=lambda _cmd, _cwd, _timeout: (False, "probe failure"),
        )
        actual = decision.action.upper() if decision else "ALLOW"
        return actual == "DENY", f"commit {sample_file} with failing check", "BLOCK", actual

    return False, kind or "unknown", "SUPPORTED GUARD", "UNKNOWN"
