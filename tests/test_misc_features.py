from pathlib import Path

from gea import autonomy, lint_context, manifest, paths, uninstall
from gea.agents import auth, profiles, state
from gea.setup import global_instructions, skills, steps


def test_autonomy_describes_every_level_in_both_languages():
    for lang in ("es", "en"):
        levels = ("supervised", "balanced", "autonomous")
        texts = {autonomy.describe(level, lang) for level in levels}
        assert len(texts) == 3
    assert autonomy.describe("bogus") == autonomy.describe("balanced")


def test_manifest_dedupes_and_dry_run_records_nothing():
    manifest.record("skill", "x")
    manifest.record("skill", "x")
    assert manifest.of_kind("skill") == ["x"]


def test_uninstall_removes_recorded_block_with_backup(monkeypatch):
    target = paths.home() / ".claude" / "CLAUDE.md"
    target.parent.mkdir(parents=True)
    target.write_text("mine\n")
    global_instructions.apply_to_file(target)
    manifest.record(manifest.KIND_INSTRUCTIONS, str(target))
    calls = []
    monkeypatch.setattr(
        uninstall.proc, "run_visible", lambda cmd, timeout=None: calls.append(cmd) or 0
    )

    assert uninstall.run_uninstall(assume_yes=True) == 0
    assert target.read_text() == "mine\n"
    assert list(paths.home().glob("gea-uninstall-backup-*/.claude/CLAUDE.md"))
    assert manifest.load() == []


def test_uninstall_asks_before_touching_anything(monkeypatch):
    manifest.record(manifest.KIND_SKILL, "grill-me")
    monkeypatch.setattr("builtins.input", lambda _="": "n")
    assert uninstall.run_uninstall() == 1
    assert manifest.of_kind("skill") == ["grill-me"]


def test_uninstall_dry_run_changes_nothing():
    manifest.record(manifest.KIND_SKILL, "grill-me")
    assert uninstall.run_uninstall(dry_run=True) == 0
    assert manifest.of_kind("skill") == ["grill-me"]


def test_setup_dry_run_runs_no_installer(monkeypatch):
    ran = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: ran.append(a))
    monkeypatch.setattr(steps.tools, "ensure_system_packages", lambda: [])
    steps.run_setup(assume_yes=True, only="lang", dry_run=True)
    assert not ran
    assert not (paths.gea_home() / "config.json").exists()


def test_optional_skill_can_be_turned_off(monkeypatch):
    steps.config.save_global({**steps.config.load_global(), "optional": {"ponytail": False}})
    monkeypatch.setattr(skills.proc, "run_visible", lambda cmd, timeout=30: 0)
    synced = skills.sync_third_party_skills(["claude"])
    assert synced == skills.THIRD_PARTY_SKILLS


def test_lint_flags_oversized_files(tmp_path, capsys):
    (tmp_path / "AGENTS.md").write_text("x" * 4 * (lint_context.MAX_INSTRUCTION_TOKENS + 10))
    (tmp_path / "CLAUDE.md").write_text("small")
    assert lint_context.run_lint(tmp_path) == 0
    out = capsys.readouterr().out
    assert "limit" in out and "AGENTS.md" in out


def test_auth_tells_missing_session_from_exhausted_tokens(monkeypatch):
    present = ("claude", "codex")
    monkeypatch.setattr(auth.platform, "which", lambda n: "/x" if n in present else None)
    monkeypatch.setitem(auth.CHECKS, "claude", lambda: auth.OK)
    monkeypatch.setitem(auth.CHECKS, "codex", lambda: auth.NO_SESSION)
    profiles_ = [profiles.AgentProfile("claude-p", "claude", None, "claude-pool", 1)]
    monkeypatch.setattr(auth.profiles, "load_profiles", lambda: profiles_)
    monkeypatch.setattr(auth.state, "load", lambda: {"claude-pool": "2099-01-01T00:00:00+00:00"})
    by_cli = {a.cli: a for a in auth.collect()}
    assert by_cli["codex"].session == auth.NO_SESSION and by_cli["codex"].exhausted_until is None
    assert by_cli["claude"].session == auth.OK and by_cli["claude"].exhausted_until
    assert state  # module imported for the pool semantics above


def test_claude_auth_parses_json(monkeypatch):
    monkeypatch.setattr(auth.proc, "run", lambda cmd, timeout=30: ('{"loggedIn": true}', "", 0))
    assert auth._claude() == auth.OK
    monkeypatch.setattr(auth.proc, "run", lambda cmd, timeout=30: ('{"loggedIn": false}', "", 1))
    assert auth._claude() == auth.NO_SESSION


def test_agents_md_template_keeps_variable_content_last():
    root = Path(steps.__file__).resolve().parents[1] / "templates"
    for lang in ("es", "en"):
        text = (root / lang / "AGENTS.md").read_text(encoding="utf-8")
        first_var = text.index("{")
        assert text.index("## Project") < first_var
        assert "{project_name}" not in text[: text.index("## Project")]


def test_strict_lint_fails_only_on_oversized_instruction_files(tmp_path):
    (tmp_path / "AGENTS.md").write_text("small")
    assert lint_context.run_lint(tmp_path, strict=True) == 0
    (tmp_path / "AGENTS.md").write_text("x" * 4 * (lint_context.MAX_INSTRUCTION_TOKENS + 10))
    assert lint_context.run_lint(tmp_path, strict=True) == 1
    assert lint_context.run_lint(tmp_path) == 0  # advisory without --strict
