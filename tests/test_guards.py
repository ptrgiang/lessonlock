from pathlib import Path

from lessonlock.guards import evaluate_guard


CWD = Path(".")


def test_protected_path_denies():
    guard = {"id": "g", "kind": "protected_path", "paths": ["migrations/generated/**"]}
    event = {"tool_name": "Edit", "tool_input": {"file_path": "migrations/generated/1.sql"}}
    assert evaluate_guard(guard, event, CWD).action == "deny"


def test_codex_apply_patch_protected_path_denies():
    guard = {"id": "g", "kind": "protected_path", "paths": ["migrations/generated/**"]}
    patch = """*** Begin Patch
*** Update File: migrations/generated/1.sql
@@
-old
+new
*** End Patch
"""
    event = {"tool_name": "apply_patch", "tool_input": {"command": patch}}
    assert evaluate_guard(guard, event, CWD).action == "deny"


def test_codex_apply_patch_checks_move_destination():
    guard = {"id": "g", "kind": "protected_path", "paths": ["migrations/generated/**"]}
    patch = """*** Begin Patch
*** Update File: migrations/source.sql
*** Move to: migrations/generated/1.sql
@@
-old
+new
*** End Patch
"""
    event = {"tool_name": "apply_patch", "tool_input": {"command": patch}}
    assert evaluate_guard(guard, event, CWD).action == "deny"


def test_codex_apply_patch_unrelated_path_is_not_denied():
    guard = {"id": "g", "kind": "protected_path", "paths": ["migrations/generated/**"]}
    patch = """*** Begin Patch
*** Update File: src/app.py
@@
-old
+new
*** End Patch
"""
    event = {"tool_name": "apply_patch", "tool_input": {"command": patch}}
    assert evaluate_guard(guard, event, CWD) is None


def test_command_deny_denies():
    guard = {"id": "g", "kind": "command_deny", "patterns": [r"rm\s+-rf"]}
    event = {"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}}
    assert evaluate_guard(guard, event, CWD).action == "deny"


def test_command_rewrite_updates_input():
    guard = {"id": "g", "kind": "command_rewrite", "pattern": r"\bpip\b", "replacement": "uv pip"}
    event = {"tool_name": "Bash", "tool_input": {"command": "pip install ruff"}}
    decision = evaluate_guard(guard, event, CWD)
    assert decision.action == "rewrite"
    assert decision.updated_input["command"] == "uv pip install ruff"


def test_branch_guard_denies_main():
    guard = {"id": "g", "kind": "branch_guard", "branches": ["main"]}
    event = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    decision = evaluate_guard(guard, event, CWD, get_branch=lambda _cwd: "main")
    assert decision.action == "deny"


def test_verify_before_commit_denies_failing_check():
    guard = {
        "id": "g",
        "kind": "verify_before_commit",
        "changed_paths": ["src/**"],
        "check": {"command": "pytest -q", "timeout": 10},
    }
    event = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    decision = evaluate_guard(
        guard,
        event,
        CWD,
        get_staged_files=lambda _cwd: ["src/app.py"],
        run_check=lambda *_args: (False, "1 failed"),
    )
    assert decision.action == "deny"
    assert "Verification failed" in decision.reason


def test_protected_path_handles_absolute_paths(tmp_path: Path):
    target = tmp_path / "migrations" / "generated" / "1.sql"
    guard = {"id": "g", "kind": "protected_path", "paths": ["migrations/generated/**"]}
    event = {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}
    assert evaluate_guard(guard, event, tmp_path).action == "deny"


def test_powershell_command_is_enforced():
    guard = {"id": "g", "kind": "command_deny", "patterns": [r"Remove-Item"]}
    event = {"tool_name": "PowerShell", "tool_input": {"command": "Remove-Item -Recurse build"}}
    assert evaluate_guard(guard, event, CWD).action == "deny"
