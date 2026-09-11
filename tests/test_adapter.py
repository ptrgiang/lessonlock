import json
from pathlib import Path

from lessonlock.adapters import CODEX_MATCHER, install_claude, install_codex


def test_install_claude_is_idempotent(tmp_path: Path):
    path, changed = install_claude(tmp_path)
    assert changed
    _, changed_again = install_claude(tmp_path)
    assert not changed_again
    data = json.loads(path.read_text())
    assert len(data["hooks"]["PreToolUse"]) == 1


def test_install_codex_is_idempotent(tmp_path: Path):
    path, changed = install_codex(tmp_path)
    assert changed
    assert path == tmp_path / ".codex" / "hooks.json"

    _, changed_again = install_codex(tmp_path)
    assert not changed_again

    data = json.loads(path.read_text())
    entries = data["hooks"]["PreToolUse"]
    assert len(entries) == 1
    assert entries[0]["matcher"] == CODEX_MATCHER
    assert entries[0]["hooks"][0]["command"] == "lessonlock hook pre-tool-use"
