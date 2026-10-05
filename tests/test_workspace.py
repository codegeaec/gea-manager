from gea import workspace


def _ws1(label, root):
    return workspace.Workspace("ws-1")


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
    found = workspace._find_or_create_workspace("demo", __import__("pathlib").Path("/tmp"))
    assert found == workspace.Workspace("ws-1")  # reused: no initial tab to adopt


def test_find_or_create_workspace_creates_when_absent(monkeypatch, tmp_path):
    calls = []

    def fake_herdr_json(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["workspace", "list"]:
            return {"workspaces": []}, None
        if cmd[:2] == ["workspace", "create"]:
            return {
                "workspace": {"workspace_id": "ws-new"},
                "tab": {"tab_id": "ws-new:t1"},
                "root_pane": {"pane_id": "ws-new:p1"},
            }, None
        return {}, None

    monkeypatch.setattr(workspace, "herdr_json", fake_herdr_json)
    ws = workspace._find_or_create_workspace("demo", tmp_path)
    assert ws == workspace.Workspace("ws-new", "ws-new:t1", "ws-new:p1")
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
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
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
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
    monkeypatch.setattr(workspace, "_ensure_agent_tab", lambda *a, **k: True)
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, None))
    prompts = []
    monkeypatch.setattr(
        workspace, "prompt_pane", lambda pane, msg, wait=True: prompts.append((pane, msg, wait))
    )
    workspace.open_or_focus()
    expected = workspace.agent_name(workspace.project_prefix(tmp_path), "claude")
    assert prompts == [(expected, "/model opusplan", False)]


def test_open_or_focus_does_not_set_model_when_tab_reused(monkeypatch, tmp_path):
    (tmp_path / "gea.json").write_text(
        '{"primary": "claude", "primaryModel": "opusplan"}', encoding="utf-8"
    )
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
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
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
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
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
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


class FakeHerdr:
    """Just enough of herdr for the tab logic: records every call."""

    def __init__(self, tabs=(), rename_error=None):
        self.calls = []
        self.tabs = [{"label": label, "tab_id": f"t-{label}"} for label in tabs]
        self.rename_error = rename_error

    def __call__(self, cmd, timeout=15):
        self.calls.append(cmd)
        if cmd[:2] == ["tab", "list"]:
            return {"tabs": list(self.tabs)}, None
        if cmd[:2] == ["tab", "create"]:
            label = cmd[cmd.index("--label") + 1]
            self.tabs.append({"label": label, "tab_id": f"t-{label}"})
            return {"root_pane": {"pane_id": f"pane-{label}"}}, None
        if cmd[:2] == ["tab", "rename"]:
            if self.rename_error:
                return {}, self.rename_error
            self.tabs.append({"label": cmd[3], "tab_id": cmd[2]})
            return {}, None
        return {}, None

    def named(self, *prefix):
        return [c for c in self.calls if c[: len(prefix)] == list(prefix)]


def test_new_workspace_reuses_its_first_tab_for_the_primary_agent(monkeypatch, tmp_path):
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    created = workspace._ensure_agent_tab(
        "ws-1", tmp_path, "claude", "claude", initial=("ws-1:t1", "ws-1:p1")
    )
    assert created is True
    assert herdr.named("tab", "rename") == [["tab", "rename", "ws-1:t1", "claude"]]
    assert not herdr.named("tab", "create")  # no second tab, so no stray "1"
    start = herdr.named("agent", "start")[0]
    assert start[start.index("--pane") + 1] == "ws-1:p1"


def test_falls_back_to_a_new_tab_when_the_rename_fails(monkeypatch, tmp_path):
    herdr = FakeHerdr(rename_error="nope")
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    assert workspace._ensure_agent_tab(
        "ws-1", tmp_path, "claude", "claude", initial=("ws-1:t1", "ws-1:p1")
    )
    assert herdr.named("tab", "create")


def test_existing_workspace_is_left_untouched(monkeypatch, tmp_path):
    herdr = FakeHerdr(tabs=["claude"])
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    assert workspace._ensure_agent_tab("ws-1", tmp_path, "claude", "claude") is False
    assert not herdr.named("tab", "rename") and not herdr.named("tab", "create")


def test_open_or_focus_passes_the_initial_tab_and_creates_terminal_and_extras(
    monkeypatch, tmp_path
):
    (tmp_path / "apps" / "web").mkdir(parents=True)
    (tmp_path / "gea.json").write_text(
        '{"primary": "claude", "tabs": [{"label": "web", "cwd": "apps/web"}]}'
    )
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        workspace,
        "_find_or_create_workspace",
        lambda label, root: workspace.Workspace("ws-1", "ws-1:t1", "ws-1:p1"),
    )
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    monkeypatch.setattr(workspace, "prompt_pane", lambda *a, **k: None)
    monkeypatch.setattr(workspace.platform, "which", lambda name: None)
    workspace.open_or_focus()
    labels = [c[c.index("--label") + 1] for c in herdr.named("tab", "create")]
    assert labels == ["terminal", "web"]  # no "claude" create: it adopted the initial tab
    web = next(c for c in herdr.named("tab", "create") if "web" in c)
    assert web[web.index("--cwd") + 1] == str(tmp_path / "apps" / "web")


def test_extra_tab_command_runs_once_only_when_the_tab_is_created(monkeypatch, tmp_path):
    (tmp_path / "api").mkdir()
    tabs = [{"label": "api", "cwd": "api", "command": "pnpm dev"}]
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    workspace._ensure_extra_tabs("ws-1", tmp_path, tabs)
    assert herdr.named("pane", "run") == [["pane", "run", "pane-api", "pnpm dev"]]
    workspace._ensure_extra_tabs("ws-1", tmp_path, tabs)  # reopen: tab exists now
    assert len(herdr.named("pane", "run")) == 1 and len(herdr.named("tab", "create")) == 1


def test_extra_tab_without_command_is_just_a_shell_and_missing_cwd_is_skipped(
    monkeypatch, tmp_path, capsys
):
    (tmp_path / "web").mkdir()
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    workspace._ensure_extra_tabs(
        "ws-1", tmp_path, [{"label": "gone", "cwd": "missing"}, {"label": "web", "cwd": "web"}]
    )
    assert not herdr.named("pane", "run")
    assert [c[c.index("--label") + 1] for c in herdr.named("tab", "create")] == ["web"]
    assert "missing" in capsys.readouterr().out


def test_the_agent_is_started_under_the_project_specific_name(monkeypatch, tmp_path):
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    workspace._ensure_agent_tab(
        "ws-1", tmp_path, "claude", "claude", ("t1", "p1"), agent_name="claude-demo"
    )
    assert herdr.named("agent", "start")[0][2] == "claude-demo"
    assert herdr.named("tab", "rename") == [["tab", "rename", "t1", "claude"]]  # tab label stays


def test_a_non_claude_planner_gets_its_model_as_a_start_flag(monkeypatch, tmp_path):
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    workspace._ensure_agent_tab("ws-1", tmp_path, "codex", "codex", None, "cod-codex", "gpt-5.5")
    tail = herdr.named("agent", "start")[0]
    assert tail[tail.index("--") + 1 :] == ["-m", "gpt-5.5"]


def test_claude_planner_model_is_set_through_slash_model_not_a_flag(monkeypatch, tmp_path):
    (tmp_path / "gea.json").write_text("{}")
    (tmp_path / "gea.local.json").write_text(
        '{"agents": {"planner": "claude", "plannerModel": "opusplan"}}'
    )
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(workspace, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace, "_find_or_create_workspace", _ws1)
    seen = {}
    monkeypatch.setattr(
        workspace, "_ensure_agent_tab", lambda *a, **k: seen.setdefault("model", a[6]) or True
    )
    monkeypatch.setattr(workspace, "_ensure_plain_tab", lambda *a, **k: None)
    monkeypatch.setattr(workspace, "herdr_json", lambda cmd, timeout=15: ({}, None))
    prompts = []
    monkeypatch.setattr(workspace, "prompt_pane", lambda pane, msg, wait=True: prompts.append(msg))
    workspace.open_or_focus()
    assert seen["model"] == "opusplan" and prompts == ["/model opusplan"]


def test_git_tab_runs_lazygit_when_installed(monkeypatch, tmp_path):
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    monkeypatch.setattr(workspace.platform, "which", lambda name: "/bin/lazygit")
    workspace._ensure_git_tab("ws-1", tmp_path)
    assert [c[c.index("--label") + 1] for c in herdr.named("tab", "create")] == ["git"]
    assert [c[-1] for c in herdr.named("pane", "run")] == ["/bin/lazygit"]  # absolute path


def test_git_tab_skipped_without_lazygit(monkeypatch, tmp_path):
    herdr = FakeHerdr()
    monkeypatch.setattr(workspace, "herdr_json", herdr)
    monkeypatch.setattr(workspace.platform, "which", lambda name: None)
    workspace._ensure_git_tab("ws-1", tmp_path)
    assert not herdr.named("tab", "create")

