from gea import workspace


def _ws1(label, root):
    return workspace.Workspace("ws-1")


def _revive_herdr(idle, calls, tab="git"):
    """Fake herdr: one existing tab whose pane is at its shell (idle) or busy."""

    def fake(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["tab", "list"]:
            return {"tabs": [{"label": tab, "tab_id": "t1"}]}, None
        if cmd[:2] == ["pane", "list"]:
            return {"panes": [{"pane_id": "p1", "tab_id": "t1"}]}, None
        if cmd[:2] == ["pane", "process-info"]:
            group = 10 if idle else 99
            procs = [{"argv": ["claude", "--append-system-prompt", "x"]}]
            return {"process_info": {
                "shell_pid": 10, "foreground_process_group_id": group,
                "foreground_processes": procs,
            }}, None
        return {}, None

    return fake


def test_git_tab_relaunches_lazygit_when_pane_is_at_shell(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(workspace.platform, "which", lambda name: "/bin/lazygit")
    monkeypatch.setattr(workspace, "herdr_json", _revive_herdr(True, calls))
    workspace._ensure_git_tab("ws-1", tmp_path)
    assert ["pane", "run", "p1", "/bin/lazygit"] in calls


def test_git_tab_left_alone_when_lazygit_is_running(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(workspace.platform, "which", lambda name: "/bin/lazygit")
    monkeypatch.setattr(workspace, "herdr_json", _revive_herdr(False, calls))
    workspace._ensure_git_tab("ws-1", tmp_path)
    assert not any(cmd[:2] == ["pane", "run"] for cmd in calls)


def test_agent_tab_restarts_agent_when_pane_is_at_shell(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(workspace, "herdr_json", _revive_herdr(True, calls, tab="claude"))
    assert workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude") is True
    assert any(cmd[:2] == ["agent", "start"] and "p1" in cmd for cmd in calls)


def test_agent_tab_running_in_other_mode_is_warned_not_touched(monkeypatch, tmp_path):
    calls, warns = [], []
    monkeypatch.setattr(workspace, "herdr_json", _revive_herdr(False, calls, tab="claude"))
    monkeypatch.setattr(workspace.ui, "warn", warns.append)
    assert workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude") is False
    assert warns and not any(cmd[0] == "agent" for cmd in calls)


def test_agent_tab_passes_extra_args_to_start(monkeypatch, tmp_path):
    calls = []

    def fake(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["tab", "create"]:
            return {"root_pane": {"pane_id": "p9"}}, None
        return {"tabs": []} if cmd[:2] == ["tab", "list"] else {}, None

    monkeypatch.setattr(workspace, "herdr_json", fake)
    workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude", extra_args=["--x", "y"])
    start = next(cmd for cmd in calls if cmd[:2] == ["agent", "start"])
    assert start[-2:] == ["--x", "y"]


def test_only_args_claude_only(tmp_path):
    cfg = {"workflow": "only", "lang": {"agents": "en"}}
    args = workspace._only_args(cfg, "claude")
    assert args[0] == "--append-system-prompt" and "gea --only" in args[1]
    assert workspace._only_args({"workflow": "team"}, "claude") == []
    assert workspace._only_args(cfg, "codex") == []


def test_open_or_focus_persists_workflow(monkeypatch, tmp_path):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: False)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "_ensure_git_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, None))
    workspace.open_or_focus("only")
    assert '"workflow": "only"' in (tmp_path / "gea.local.json").read_text()
    assert not (tmp_path / "gea.json").exists()
    workspace.open_or_focus("team")
    assert "workflow" not in (tmp_path / "gea.local.json").read_text()
