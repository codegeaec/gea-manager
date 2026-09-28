from gea import workspace


def test_safe_label_slugifies_name():
    assert workspace._safe_label("My Cool Project!") == "my-cool-project"
    assert workspace._safe_label("") == "repo"


def test_find_or_create_workspace_reuses_existing(monkeypatch):
    monkeypatch.setattr(
        workspace,
        "herdr_json",
        lambda cmd, timeout=15: (
            ({"workspaces": [{"label": "demo", "workspace_id": "ws-1"}]}, None)
            if cmd[0] == "workspace" and cmd[1] == "list"
            else ({}, None)
        ),
    )
    assert workspace._find_or_create_workspace("demo", __import__("pathlib").Path("/tmp")) == "ws-1"


def test_find_or_create_workspace_creates_when_absent(monkeypatch, tmp_path):
    calls = []

    def fake_herdr_json(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["workspace", "list"]:
            return {"workspaces": []}, None
        if cmd[:2] == ["workspace", "create"]:
            return {"workspace": {"workspace_id": "ws-new"}}, None
        return {}, None

    monkeypatch.setattr(workspace, "herdr_json", fake_herdr_json)
    ws_id = workspace._find_or_create_workspace("demo", tmp_path)
    assert ws_id == "ws-new"
    assert any(cmd[:2] == ["workspace", "create"] for cmd in calls)


def test_ensure_agent_tab_skips_if_tab_exists(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        workspace,
        "herdr_json",
        lambda cmd, timeout=15: (calls.append(cmd) or ({"tabs": [{"label": "claude"}]}, None)),
    )
    created = workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude")
    assert created is False
    assert not any(cmd[0] == "agent" for cmd in calls)


def test_ensure_agent_tab_creates_and_starts(monkeypatch, tmp_path):
    calls = []

    def fake_herdr_json(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["tab", "list"]:
            return {"tabs": []}, None
        if cmd[:2] == ["tab", "create"]:
            return {"root_pane": {"pane_id": "pane-1"}}, None
        if cmd[:2] == ["agent", "start"]:
            return {"agent": "started"}, None
        return {}, None

    monkeypatch.setattr(workspace, "herdr_json", fake_herdr_json)
    created = workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude")
    assert created is True
    assert any(cmd[:2] == ["agent", "start"] for cmd in calls)


def test_ensure_agent_tab_returns_false_when_start_fails(monkeypatch, tmp_path):
    def fake_herdr_json(cmd, timeout=15):
        if cmd[:2] == ["tab", "list"]:
            return {"tabs": []}, None
        if cmd[:2] == ["tab", "create"]:
            return {"root_pane": {"pane_id": "pane-1"}}, None
        if cmd[:2] == ["agent", "start"]:
            return {}, "agent_not_ready"
        return {}, None

    monkeypatch.setattr(workspace, "herdr_json", fake_herdr_json)
    created = workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude")
    assert created is False


def test_open_or_focus_execs_herdr_when_outside(monkeypatch, tmp_path):
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", lambda label, root: "ws-1")
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    execed = []
    monkeypatch.setattr(workspace.os, "execvp", lambda prog, args: execed.append((prog, args)))
    workspace.open_or_focus()
    assert execed == [("herdr", ["herdr"])]


def test_open_or_focus_sets_model_on_first_claude_tab(monkeypatch, tmp_path):
    (tmp_path / "gea.json").write_text(
        '{"primary": "claude", "primaryModel": "opusplan"}', encoding="utf-8"
    )
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", lambda label, root: "ws-1")
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: True)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, None))
    prompts = []
    monkeypatch.setattr(
        workspace, "prompt_pane", lambda pane, msg, wait=True: prompts.append((pane, msg, wait))
    )
    workspace.open_or_focus()
    assert prompts == [("claude", "/model opusplan", False)]


def test_open_or_focus_does_not_set_model_when_tab_reused(monkeypatch, tmp_path):
    (tmp_path / "gea.json").write_text(
        '{"primary": "claude", "primaryModel": "opusplan"}', encoding="utf-8"
    )
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", lambda label, root: "ws-1")
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: False)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, None))
    prompts = []
    monkeypatch.setattr(
        workspace, "prompt_pane", lambda pane, msg, wait=True: prompts.append((pane, msg, wait))
    )
    workspace.open_or_focus()
    assert prompts == []


def test_open_or_focus_does_not_set_model_without_primary_model(monkeypatch, tmp_path):
    (tmp_path / "gea.json").write_text('{"primary": "claude"}', encoding="utf-8")
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", lambda label, root: "ws-1")
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: True)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, None))
    prompts = []
    monkeypatch.setattr(
        workspace, "prompt_pane", lambda pane, msg, wait=True: prompts.append((pane, msg, wait))
    )
    workspace.open_or_focus()
    assert prompts == []


def test_open_or_focus_focuses_when_inside_herdr(monkeypatch, tmp_path):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", lambda label, root: "ws-1")
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    calls = []

    def fake_herdr_json(cmd, timeout=15):
        calls.append(cmd)
        return {}, None

    monkeypatch.setattr(workspace, "herdr_json", fake_herdr_json)
    code = workspace.open_or_focus()
    assert code == 0
    assert ["workspace", "focus", "ws-1"] in calls
