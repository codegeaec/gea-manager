from gea.init import wizard


def test_pick_primary_model_returns_none_for_non_claude():
    assert wizard._pick_primary_model("opencode") is None


def test_pick_primary_model_returns_opusplan_when_accepted(monkeypatch):
    monkeypatch.setattr(wizard.ui, "ask_yes_no", lambda *a, **k: True)
    assert wizard._pick_primary_model("claude") == "opusplan"


def test_pick_primary_model_returns_none_when_declined(monkeypatch):
    monkeypatch.setattr(wizard.ui, "ask_yes_no", lambda *a, **k: False)
    assert wizard._pick_primary_model("claude") is None


import subprocess  # noqa: E402

import pytest  # noqa: E402

from gea import config  # noqa: E402


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
