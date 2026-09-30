import json

import pytest

from gea import config, paths, ui
from gea.agents import cli as agents_cli
from gea.agents import manage, models, spec
from gea.agents.profiles import AgentProfile
from gea.agents.spec import AgentsSpec


def detected():
    return [
        AgentProfile("oc-kimi", "opencode", "opencode-go/kimi-k2.7-code", "opencode-go", 1),
        AgentProfile("agy", "agy", None, "agy-gemini", 10),
        AgentProfile("codex", "codex", None, "codex", 11),
    ]


# ----- pure edits ---------------------------------------------------------------------


def test_the_first_edit_materialises_every_detected_profile():
    got = manage.remove(AgentsSpec(), "agy", detected())
    assert got.subagents == ["oc-kimi", "codex"]


def test_add_detected_and_its_errors():
    base = AgentsSpec(subagents=["codex"])
    assert manage.add_detected(base, "agy", detected()).subagents == ["codex", "agy"]
    with pytest.raises(ValueError, match="already"):
        manage.add_detected(base, "codex", detected())
    with pytest.raises(ValueError, match="not a detected"):
        manage.add_detected(base, "ghost", detected())


def test_add_custom_validates_and_keeps_model_and_pool():
    got = manage.add_custom(
        AgentsSpec(subagents=["codex"]),
        "oc-lite",
        "opencode",
        "opencode-go/deepseek-v4-flash",
        "opencode-go",
        detected(),
    )
    assert got.subagents[1] == {
        "id": "oc-lite",
        "cli": "opencode",
        "model": "opencode-go/deepseek-v4-flash",
        "pool": "opencode-go",
    }
    with pytest.raises(ValueError):
        manage.add_custom(got, "Bad Id", "opencode", None, None, detected())
    with pytest.raises(ValueError):
        manage.add_custom(got, "x", "vim", None, None, detected())
    with pytest.raises(ValueError, match="already"):
        manage.add_custom(got, "oc-lite", "opencode", None, None, detected())


def test_changing_a_model_turns_a_detected_profile_into_an_override_and_back():
    value = AgentsSpec(subagents=["oc-kimi", "codex"])
    over = manage.set_subagent_model(value, "oc-kimi", "opencode-go/other", detected())
    assert over.subagents[0] == {"id": "oc-kimi", "model": "opencode-go/other"}
    back = manage.set_subagent_model(over, "oc-kimi", None, detected())
    assert back.subagents[0] == "oc-kimi"


def test_changing_a_custom_model_edits_it_in_place_and_none_clears_it():
    value = AgentsSpec(subagents=[{"id": "c", "cli": "opencode", "model": "a/b", "pool": "p"}])
    got = manage.set_subagent_model(value, "c", "a/z", detected())
    assert got.subagents[0] == {"id": "c", "cli": "opencode", "model": "a/z", "pool": "p"}
    cleared = manage.set_subagent_model(got, "c", None, detected())
    assert cleared.subagents[0] == {"id": "c", "cli": "opencode", "pool": "p"}


def test_move_changes_priority_and_clamps_and_unknown_ids_raise():
    value = AgentsSpec(subagents=["a", "b", "c"])
    assert manage.move(value, "c", -1, detected()).subagents == ["a", "c", "b"]
    assert manage.move(value, "a", -5, detected()).subagents == ["a", "b", "c"]
    with pytest.raises(ValueError):
        manage.move(value, "zzz", 1, detected())


def test_removing_the_last_subagent_goes_back_to_all_detected():
    assert manage.remove(AgentsSpec(subagents=["codex"]), "codex", detected()).subagents is None


def test_describe_shows_origin_and_flags_a_model_the_cli_no_longer_lists(monkeypatch):
    monkeypatch.setattr(models, "list_models", lambda cli, refresh=False: [models.Model("ok/m")])
    value = AgentsSpec(
        subagents=[
            "codex",
            {"id": "oc-kimi", "model": "gone/model"},
            {"id": "lite", "cli": "opencode", "model": "ok/m"},
        ]
    )
    lines = manage.describe(value, detected())
    assert "[detected]" in lines[0] and "[override]" in lines[1] and "⚠" in lines[1]
    assert "[custom]" in lines[2] and "⚠" not in lines[2]


def test_suggested_ids_are_valid():
    assert (
        manage.suggest_id("opencode", "opencode-go/DeepSeek-V4 Pro") == "opencode-deepseek-v4-pro"
    )
    assert manage.suggest_id("codex", None) == "codex-default"
    assert spec.ID_RE.fullmatch(manage.suggest_id("agy", "gemini-3.1-pro-high"))


# ----- the picker -----------------------------------------------------------------------


def _typed(monkeypatch, *answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _="": next(it))


def test_ask_pick_number_filter_default_and_free_text(monkeypatch, capsys):
    options = [f"opt-{i}" for i in range(30)] + ["special-one"]
    _typed(monkeypatch, "3")
    assert ui.ask_pick("q", options) == "opt-2"
    _typed(monkeypatch, "special", "1")  # filter, then take the first match
    assert ui.ask_pick("q", options) == "special-one"
    _typed(monkeypatch, "")
    assert ui.ask_pick("q", options, default="opt-9") == "opt-9"
    _typed(monkeypatch, "brand-new")
    assert ui.ask_pick("q", options, free_text=True) == "brand-new"
    _typed(monkeypatch, "zzz", "")  # no match without free text: shown again, then default
    assert ui.ask_pick("q", options, default="opt-1") == "opt-1"
    assert "more" in capsys.readouterr().out


def test_ask_pick_never_loops_forever(monkeypatch):
    _typed(monkeypatch, *(["99"] * 60))
    assert ui.ask_pick("q", ["a", "b"]) is None


def test_pick_model_reads_the_clis_list_and_can_choose_the_default(monkeypatch):
    monkeypatch.setattr(
        models,
        "list_models",
        lambda cli, refresh=False: [models.Model("a/one", "First"), models.Model("a/two")],
    )
    monkeypatch.setattr(models, "is_known", lambda cli, m: True)
    _typed(monkeypatch, "3")  # options: default, "a/one  First", "a/two"
    assert manage.pick_model("opencode") == "a/two"
    _typed(monkeypatch, "1")
    assert manage.pick_model("opencode") is None
    assert manage.pick_model("opencode", default="a/two", assume_yes=True) == "a/two"


def test_pick_model_asks_for_text_when_the_cli_cannot_list(monkeypatch):
    monkeypatch.setattr(models, "list_models", lambda cli, refresh=False: None)
    _typed(monkeypatch, "kimi-k2")
    assert manage.pick_model("kimi") == "kimi-k2"


def test_prompt_planner_suggests_opusplan_for_claude(monkeypatch):
    monkeypatch.setattr(manage, "installed_clis", lambda: ["claude", "codex"])
    monkeypatch.setattr(models, "list_models", lambda cli, refresh=False: None)
    assert manage.prompt_planner(AgentsSpec(), assume_yes=True) == AgentsSpec("claude", "opusplan")
    monkeypatch.setattr(ui, "ask_choice", lambda *a, **k: 1)
    _typed(monkeypatch, "gpt-5.5")
    assert manage.prompt_planner(AgentsSpec()) == AgentsSpec("codex", "gpt-5.5")


# ----- persistence: the menu and the commands write the right key ------------------------


@pytest.fixture
def project(tmp_path, monkeypatch):
    paths.gea_home().mkdir(parents=True, exist_ok=True)
    profs = [p.to_dict() for p in detected()]
    paths.global_config_path().write_text(json.dumps({"builders": {"profiles": profs}}))
    (tmp_path / "gea.json").write_text(json.dumps({"name": "demo", "verify": ["x"]}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(models, "list_models", lambda cli, refresh=False: None)
    return tmp_path


def _saved(project):
    local = project / "gea.local.json"
    return json.loads(local.read_text()).get("agents") if local.exists() else None


def test_commands_write_agents_to_the_personal_file_only(project, capsys):
    assert agents_cli.cmd_planner("codex", "gpt-5.5") == 0
    assert agents_cli.cmd_add("oc-lite", "opencode", "opencode-go/deepseek-v4-flash", None) == 0
    assert agents_cli.cmd_add("agy", None, None, None) == 1  # already there (materialised)
    saved = _saved(project)
    assert saved["planner"] == "codex" and saved["plannerModel"] == "gpt-5.5"
    assert saved["subagents"][-1]["id"] == "oc-lite"  # appended after the detected ones
    assert "agents" not in json.loads((project / "gea.json").read_text())
    assert agents_cli.cmd_remove("oc-lite") == 0
    assert agents_cli.cmd_remove("nope") == 1
    assert agents_cli.cmd_planner("emacs", None) == 1
    assert "unknown CLI" in capsys.readouterr().out


def test_list_shows_planner_subagents_and_unknown_ids(project, capsys):
    (project / "gea.local.json").write_text(
        json.dumps({"agents": {"planner": "codex", "subagents": ["agy", "ghost"]}})
    )
    assert agents_cli.cmd_list() == 0
    out = capsys.readouterr().out
    assert "planner = codex" in out and "agy" in out and "ghost" in out


def test_available_and_check_use_the_projects_resolved_subagents(project, capsys):
    (project / "gea.local.json").write_text(
        json.dumps(
            {
                "agents": {
                    "subagents": [{"id": "oc-lite", "cli": "opencode", "model": "opencode-go/x"}]
                }
            }
        )
    )
    agents_cli.cmd_available()
    out = capsys.readouterr().out
    assert "oc-lite" in out and "codex" not in out
    assert agents_cli.cmd_reset("oc-lite") == 0  # a custom id is a known agent


def test_menu_add_custom_change_model_reorder_and_save(project, monkeypatch, capsys):
    monkeypatch.setattr(manage, "installed_clis", lambda: ["opencode", "codex"])
    monkeypatch.setattr(
        models,
        "list_models",
        lambda cli, refresh=False: (
            [models.Model("opencode-go/lite")] if cli == "opencode" else None
        ),
    )
    monkeypatch.setattr(models, "is_known", lambda cli, m: True)
    monkeypatch.setattr(manage, "prompt_planner", lambda value, assume_yes=False: value)
    # add -> "+ custom" (number 4 after the 3 detected? all detected are already in), so custom is 1
    answers = iter(
        [
            "a",
            "1",  # add: pick "+ custom"
            "1",  # CLI: opencode
            "2",  # model: "opencode-go/lite" (1 is the CLI default)
            "",  # id: suggested
            "",  # pool: suggested
            "o",
            "4",
            "u",  # move the new one up
            "q",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    assert manage.run_manage() == 0
    saved = _saved(project)
    assert (
        saved["subagents"][2]["id"] == "opencode-lite"
        and saved["subagents"][2]["cli"] == "opencode"
    )
    assert saved["subagents"][2]["pool"] == "opencode-go"
    assert [spec.entry_id(e) for e in saved["subagents"]] == [
        "oc-kimi",
        "agy",
        "opencode-lite",
        "codex",
    ]


def test_menu_quit_without_saving_writes_nothing(project, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _="": "x")
    assert manage.run_manage() == 1
    assert not (project / "gea.local.json").exists()


def test_menu_reports_a_bad_edit_and_keeps_going(project, monkeypatch, capsys):
    answers = iter(["r", "1", "q"])  # remove the first detected: fine, then save
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    monkeypatch.setattr(ui, "ask_choice", lambda *a, **k: 0)
    assert manage.run_manage() == 0
    assert _saved(project)["subagents"] == ["agy", "codex"]
    assert config.agents(config.load_project(project)).subagents == ["agy", "codex"]
