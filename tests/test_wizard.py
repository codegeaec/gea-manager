import json  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402

from gea import config  # noqa: E402
from gea.init import wizard


@pytest.fixture
def repo(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(wizard.platform, "which", lambda n: "/x" if n == "claude" else None)
    monkeypatch.setattr(wizard, "load_profiles", lambda: [])
    monkeypatch.setattr(wizard, "refresh_and_save", lambda: [])
    return tmp_path


def test_each_language_is_chosen_separately(repo):
    assert wizard.run_init(assume_yes=True, langs=("en", "es", "es")) == 0
    cfg = config.load_project(repo)
    assert cfg["lang"] == {"agents": "en", "docs": "es", "commits": "es"}
    assert "Shared rules for AI agents" in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "Builder instructions" in (repo / ".agents" / "builder.md").read_text(encoding="utf-8")
    assert (repo / "docs" / "00-vision-producto.md").exists()  # docs follow their own language


def test_defaults_chain_from_the_first_answer(repo):
    wizard.run_init(assume_yes=True, langs=("en", None, None))
    assert config.load_project(repo)["lang"] == {"agents": "en", "docs": "en", "commits": "en"}


def test_agents_lang_falls_back_to_docs_for_old_projects():
    assert config.agents_lang({"lang": {"docs": "en", "commits": "es"}}) == "en"
    assert config.agents_lang({"lang": {"agents": "es", "docs": "en"}}) == "es"
    assert config.agents_lang({}) == "en"


def test_interactive_questions_default_to_the_previous_answer(monkeypatch):
    asked = []

    def choice(question, options, default_index=0, assume_yes=False):
        asked.append((question, default_index))
        return 1 if len(asked) == 1 else default_index  # agents=English, accept the rest

    monkeypatch.setattr(wizard.ui, "ask_choice", choice)
    assert wizard._pick_langs() == ("en", "en", "en")
    assert [d for _q, d in asked] == [0, 1, 1]


def test_ask_multi_parses_numbers_and_defaults(monkeypatch):
    from gea import ui

    answers = iter(["", "2", "1, 3", "9", "x"])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    opts = ["a", "b", "c"]
    assert ui.ask_multi("q", opts) == [0, 1, 2]
    assert ui.ask_multi("q", opts) == [1]
    assert ui.ask_multi("q", opts) == [0, 2]
    assert ui.ask_multi("q", opts) == [0, 1, 2]  # out of range -> default
    assert ui.ask_multi("q", opts, default_all=False) == []  # not a number -> default
    assert ui.ask_multi("q", opts, assume_yes=True) == [0, 1, 2]



def test_wizard_writes_planner_and_model_into_the_personal_agents_key(repo):
    wizard.run_init(assume_yes=True, langs=("es", "es", "es"))
    local = json.loads((repo / "gea.local.json").read_text())
    assert local["agents"] == {"planner": "claude", "plannerModel": "opusplan"}
    shared = json.loads((repo / "gea.json").read_text())
    assert not {"primary", "primaryModel", "agents"} & set(shared)


def test_pick_agents_keeps_all_detected_unless_the_user_narrows_them(monkeypatch):
    from gea.agents.profiles import AgentProfile

    monkeypatch.setattr(wizard.manage, "installed_clis", lambda: ["claude"])
    profs = [AgentProfile("a", "a", None, "pa", 1), AgentProfile("b", "b", "m", "pb", 2)]
    assert wizard._pick_agents(profs, assume_yes=True).subagents is None
    monkeypatch.setattr(wizard.ui, "ask_multi", lambda *a, **k: [1])
    monkeypatch.setattr(wizard.ui, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(wizard.manage, "pick_model", lambda *a, **k: None)
    monkeypatch.setattr(wizard.ui, "ask_yes_no", lambda *a, **k: False)
    assert wizard._pick_agents(profs).subagents == ["b"]
    assert wizard._pick_agents([], assume_yes=True).subagents is None


def test_pick_agents_can_add_a_custom_subagent(monkeypatch):
    from gea.agents import spec
    from gea.agents.profiles import AgentProfile

    monkeypatch.setattr(wizard.manage, "installed_clis", lambda: ["claude"])
    monkeypatch.setattr(wizard.ui, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(wizard.manage, "pick_model", lambda *a, **k: None)
    monkeypatch.setattr(wizard.ui, "ask_multi", lambda *a, **k: [0])
    answers = iter([True, False])  # add one custom, then stop
    monkeypatch.setattr(wizard.ui, "ask_yes_no", lambda *a, **k: next(answers))
    custom = spec.AgentsSpec("claude", None, ["a", {"id": "x", "cli": "opencode"}])
    monkeypatch.setattr(wizard.manage, "prompt_custom", lambda value, det: custom)
    got = wizard._pick_agents([AgentProfile("a", "a", None, "pa", 1)])
    assert got.subagents == ["a", {"id": "x", "cli": "opencode"}]
