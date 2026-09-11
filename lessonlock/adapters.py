from __future__ import annotations

import json
from pathlib import Path


HOOK_COMMAND = "lessonlock hook pre-tool-use"


def install_claude(root: Path) -> tuple[Path, bool]:
    settings_path = root / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    entry = {
        "matcher": "Bash|PowerShell|Edit|Write",
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

    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return settings_path, not exists
