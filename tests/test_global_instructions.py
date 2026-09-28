from gea.setup import global_instructions as gi


def test_apply_to_file_creates_new_file(tmp_path):
    target = tmp_path / "CLAUDE.md"
    changed = gi.apply_to_file(target)
    assert changed is True
    content = target.read_text(encoding="utf-8")
    assert gi.START_MARKER in content
    assert "shadcn" in content.lower()
    assert "400 lines" in content


def test_apply_to_file_preserves_user_content(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My project\n\nSome custom notes.\n", encoding="utf-8")
    gi.apply_to_file(target)
    content = target.read_text(encoding="utf-8")
    assert "Some custom notes." in content
    assert gi.START_MARKER in content


def test_apply_to_file_replaces_existing_block_idempotently(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My project\n\nNotes.\n", encoding="utf-8")
    gi.apply_to_file(target)
    first = target.read_text(encoding="utf-8")
    changed_again = gi.apply_to_file(target)
    second = target.read_text(encoding="utf-8")
    assert first == second
    assert changed_again is False


def test_apply_for_installed_agents_skips_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(gi, "TARGETS", {"claude": "CLAUDE.md"})
    monkeypatch.setattr(gi.paths, "home", lambda: tmp_path)
    changed = gi.apply_for_installed_agents(["claude", "made-up-agent"])
    assert changed == [str(tmp_path / "CLAUDE.md")]
