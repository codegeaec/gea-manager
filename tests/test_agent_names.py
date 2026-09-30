import re
from pathlib import Path

from gea.agents import herdr


def test_prefix_is_the_first_three_letters_of_the_folder():
    assert herdr.project_prefix(Path("/x/cotizaciones")) == "cot"
    assert herdr.project_prefix(Path("/x/gea-manager")) == "gea"
    assert herdr.project_prefix(Path("/x/My App!")) == "mya"  # punctuation is skipped
    assert herdr.project_prefix(Path("/x/ab")) == "ab"


def test_prefix_always_starts_with_a_letter():
    for folder in ("3d-viewer", "2024", "___", ""):
        prefix = herdr.project_prefix(Path("/x") / folder)
        assert re.fullmatch(r"[a-z][a-z0-9]{0,2}", prefix), (folder, prefix)


def test_agent_names_follow_herdrs_rules():
    assert herdr.agent_name("cot", "claude") == "cot-claude"
    assert herdr.agent_name("cot", "builder", "oc-kimi") == "cot-builder-oc-kimi"
    long = herdr.agent_name("cot", "orchestrator", "x" * 40)
    assert len(long) <= 32 and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", long)
    assert not herdr.agent_name("cot", "a" * 28 + "-b").endswith(("-", "_"))


def _herdr(monkeypatch, live):
    """`live` maps agent name -> workspace id."""
    monkeypatch.setenv("HERDR_ENV", "1")

    def fake(cmd, timeout=15):
        if cmd[:2] == ["agent", "get"] and cmd[2] in live:
            return {"agent": {"name": cmd[2], "workspace_id": live[cmd[2]]}}, None
        return {}, "agent_not_found"

    monkeypatch.setattr(herdr, "herdr_json", fake)


def test_a_free_name_is_used_as_is(monkeypatch):
    _herdr(monkeypatch, {})
    assert herdr.free_agent_name("cot-claude", "wA") == "cot-claude"


def test_our_own_agent_keeps_its_name_so_the_pane_is_reused(monkeypatch):
    _herdr(monkeypatch, {"cot-claude": "wA"})
    assert herdr.free_agent_name("cot-claude", "wA") == "cot-claude"


def test_a_name_held_by_another_workspace_gets_a_suffix(monkeypatch):
    """Two projects sharing a prefix (cotizaciones / cotizador) must not collide."""
    _herdr(monkeypatch, {"cot-claude": "wA", "cot-claude-2": "wB"})
    assert herdr.free_agent_name("cot-claude", "wC") == "cot-claude-3"
    assert herdr.free_agent_name("cot-claude", "wB") == "cot-claude-2"  # already ours: reused
    assert herdr.free_agent_name("cot-claude", "wA") == "cot-claude"


def test_outside_herdr_nothing_is_queried(monkeypatch):
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.setattr(herdr, "herdr_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert herdr.free_agent_name("cot-claude", "wA") == "cot-claude"


def test_pane_name_for_combines_prefix_role_and_workspace(monkeypatch, tmp_path):
    project = tmp_path / "cotizaciones"
    project.mkdir()
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "wB")
    _herdr(monkeypatch, {"cot-builder-codex": "wA"})
    assert herdr.pane_name_for(project, "builder", "codex") == "cot-builder-codex-2"
    assert herdr.pane_name_for(project, "builder", "agy") == "cot-builder-agy"


def test_workspace_starts_the_primary_agent_as_prefix_dash_cli(monkeypatch, tmp_path):
    from gea import workspace

    project = tmp_path / "cotizaciones"
    project.mkdir()
    (project / "gea.json").write_text('{"primary": "claude"}')
    started = []
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: project)
    monkeypatch.setattr(
        workspace, "_find_or_create_workspace", lambda label, root: workspace.Workspace("wA")
    )
    monkeypatch.setattr(
        workspace, "_ensure_agent_tab", lambda *a, **k: started.append(a[-1]) or False
    )
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, "agent_not_found"))
    monkeypatch.setattr(herdr, "herdr_json", lambda cmd, timeout=15: ({}, "agent_not_found"))
    workspace.open_or_focus()
    assert started == ["cot-claude"]
