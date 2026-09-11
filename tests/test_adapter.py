import json
from pathlib import Path

from lessonlock.adapters import install_claude


def test_install_claude_is_idempotent(tmp_path: Path):
    path, changed = install_claude(tmp_path)
    assert changed
    _, changed_again = install_claude(tmp_path)
    assert not changed_again
    data = json.loads(path.read_text())
    assert len(data["hooks"]["PreToolUse"]) == 1
