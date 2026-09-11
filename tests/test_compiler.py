from lessonlock.compiler import compile_correction


def test_protected_path():
    result = compile_correction("Never edit `migrations/generated/**` again.")
    assert result.enforceable
    assert result.guard["kind"] == "protected_path"


def test_command_deny():
    result = compile_correction("Never run `rm -rf /`.")
    assert result.guard["kind"] == "command_deny"


def test_command_rewrite():
    result = compile_correction("Use `uv pip` instead of `pip`.")
    assert result.guard["kind"] == "command_rewrite"
    assert result.guard["replacement"] == "uv pip"


def test_branch_guard():
    result = compile_correction("Never commit directly to branch `main`.")
    assert result.guard["kind"] == "branch_guard"


def test_verify_before_commit():
    result = compile_correction("Before commit, run `pytest -q` after changing `src/**`.")
    assert result.guard["kind"] == "verify_before_commit"


def test_vague_correction_stays_advisory():
    result = compile_correction("Write cleaner code next time.")
    assert not result.enforceable
