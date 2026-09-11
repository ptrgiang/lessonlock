from __future__ import annotations

import json
from pathlib import Path


HOOK_COMMAND = "lessonlock hook pre-tool-use"
CLAUDE_MATCHER = "Bash|PowerShell|Edit|Write"
CODEX_MATCHER = r"^(Bash|Edit|Write|apply_patch)$"


def _install_pre_tool_use_hook(path: Path, matcher: str) -> tuple[Path, bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    entry = {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 180}],
    }

    exists = any(
        isinstance(item, dict)
        and any(
            isinstance(h, dict) and h.get("command") == HOOK_COMMAND
            for h in item.get("hooks", [])
        )
        for item in pre
    )
    if not exists:
        pre.append(entry)

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path, not exists


def install_claude(root: Path) -> tuple[Path, bool]:
    return _install_pre_tool_use_hook(root / ".claude" / "settings.json", CLAUDE_MATCHER)


def install_codex(root: Path) -> tuple[Path, bool]:
    return _install_pre_tool_use_hook(root / ".codex" / "hooks.json", CODEX_MATCHER)
