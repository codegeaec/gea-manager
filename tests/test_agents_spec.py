import json

import pytest

from gea import config, paths
from gea.agents import models, profiles, spec, state


def _detected():
    return [
        profiles.AgentProfile(
            "oc-kimi", "opencode", "opencode-go/kimi-k2.7-code", "opencode-go", 1
        ),
        profiles.AgentProfile("agy", "agy", None, "agy-gemini", 10),
        profiles.AgentProfile("codex", "codex", None, "codex", 11),
    ]


def test_new_key_and_legacy_keys_normalize_to_the_same_thing():
    new = spec.from_config(
        {"agents": {"planner": "codex", "plannerModel": "gpt-5.5", "subagents": ["agy"]}}
    )
    old = spec.from_config(
        {"primary": "codex", "primaryModel": "gpt-5.5", "builders": {"allow": ["agy"]}}
    )
    assert new == old == spec.AgentsSpec("codex", "gpt-5.5", ["agy"])
    assert spec.from_config({}) == spec.AgentsSpec("claude", None, None)


def test_the_new_key_wins_over_the_legacy_ones_key_by_key():
    got = spec.from_config(
        {"primary": "codex", "primaryModel": "old", "agents": {"plannerModel": "new"}}
    )
    assert (got.planner, got.planner_model) == ("codex", "new")


def test_to_dict_omits_defaults():
    assert spec.AgentsSpec().to_dict() == {}
    assert spec.AgentsSpec("claude", "opusplan").to_dict() == {
        "planner": "claude",
        "plannerModel": "opusplan",
    }


@pytest.mark.parametrize(
    "value",
    [
        "x",
        {"planner": "emacs"},
        {"plannerModel": 3},
        {"subagents": "codex"},
        {"subagents": [{"cli": "codex"}]},  # no id
        {"subagents": ["Bad Id"]},
        {"subagents": ["a", {"id": "a", "cli": "codex"}]},  # duplicated
        {"subagents": [{"id": "a", "cli": "vim"}]},
        {"subagents": [{"id": "a", "cli": "codex", "model": 3}]},
        {"subagents": [{"id": "a", "cli": "codex", "pool": []}]},
    ],
)
def test_invalid_agents_are_refused(tmp_path, value):
    (tmp_path / "gea.json").write_text(json.dumps({"agents": value}))
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)


def test_a_bad_local_agents_is_refused_too(tmp_path):
    (tmp_path / "gea.local.json").write_text(json.dumps({"agents": {"planner": "emacs"}}))
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)


def test_no_subagents_means_every_detected_profile():
    assert [p.id for p in profiles.resolve_subagents({}, _detected())] == [
        "oc-kimi",
        "agy",
        "codex",
    ]


def test_order_is_priority_and_unknown_ids_are_skipped_but_reported():
    cfg = {"agents": {"subagents": ["codex", "ghost", "oc-kimi"]}}
    got = profiles.resolve_subagents(cfg, _detected())
    assert [(p.id, p.priority) for p in got] == [("codex", 1), ("oc-kimi", 3)]
    assert profiles.unknown_subagent_ids(cfg, _detected()) == ["ghost"]


def test_override_changes_the_model_and_recomputes_the_pool_only_when_needed():
    cfg = {
        "agents": {
            "subagents": [
                {"id": "oc-kimi", "model": "opencode-go/other"},
                {"id": "agy", "model": "claude-sonnet-4-6"},
                {"id": "codex", "model": "gpt-5.5"},
            ]
        }
    }
    kimi, agy, codex = profiles.resolve_subagents(cfg, _detected())
    assert (kimi.model, kimi.pool, kimi.cli) == ("opencode-go/other", "opencode-go", "opencode")
    assert (agy.model, agy.pool) == ("claude-sonnet-4-6", "agy-claude")
    assert (codex.model, codex.pool) == ("gpt-5.5", "codex")


def test_custom_subagent_gets_a_sensible_default_pool():
    cfg = {
        "agents": {
            "subagents": [
                {"id": "oc-lite", "cli": "opencode", "model": "opencode-go/deepseek-v4-flash"},
                {"id": "oc-zen", "cli": "opencode", "model": "opencode/big-pickle"},
                {"id": "ag-gpt", "cli": "agy", "model": "gpt-oss-120b-medium"},
                {"id": "cx", "cli": "codex", "model": "gpt-5.5"},
                {"id": "own", "cli": "opencode", "model": "x/y", "pool": "mine"},
            ]
        }
    }
    pools = {p.id: p.pool for p in profiles.resolve_subagents(cfg, [])}
    assert pools == {
        "oc-lite": "opencode-go",
        "oc-zen": "opencode",
        "ag-gpt": "agy-gpt-oss",
        "cx": "codex",
        "own": "mine",
    }


def test_a_custom_sharing_a_pool_is_skipped_when_that_pool_is_exhausted(tmp_path, monkeypatch):
    paths.gea_home().mkdir(parents=True, exist_ok=True)
    detected = [p.to_dict() for p in _detected()]
    paths.global_config_path().write_text(json.dumps({"builders": {"profiles": detected}}))
    (tmp_path / "gea.json").write_text("{}")
    (tmp_path / "gea.local.json").write_text(
        json.dumps(
            {
                "agents": {
                    "subagents": [
                        "oc-kimi",
                        {
                            "id": "oc-lite",
                            "cli": "opencode",
                            "model": "opencode-go/deepseek-v4-flash",
                        },
                        "codex",
                    ]
                }
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    assert profiles.pick_agent().id == "oc-kimi"
    state.mark_exhausted("opencode-go", state.now().replace(year=2099))
    assert profiles.pick_agent().id == "codex"  # the custom one shares the exhausted pool
    assert profiles.pick_agent("oc-lite") is None


def test_saving_migrates_the_old_keys_to_agents_in_the_personal_file(tmp_path):
    (tmp_path / "gea.json").write_text(
        json.dumps(
            {
                "primary": "codex",
                "primaryModel": "gpt-5.5",
                "builders": {"allow": ["agy"], "ponytail": True},
            }
        )
    )
    cfg = config.load_project(tmp_path)
    assert config.agents(cfg) == spec.AgentsSpec("codex", "gpt-5.5", ["agy"])
    config.save_project(tmp_path, cfg)
    shared = json.loads((tmp_path / "gea.json").read_text())
    local = json.loads((tmp_path / "gea.local.json").read_text())
    assert not {"primary", "primaryModel", "agents"} & set(shared)
    assert "allow" not in shared["builders"]
    assert local["agents"] == {"planner": "codex", "plannerModel": "gpt-5.5", "subagents": ["agy"]}
    assert config.agents(config.load_project(tmp_path)) == spec.AgentsSpec(
        "codex", "gpt-5.5", ["agy"]
    )


def test_tab_labels_may_not_clash_with_the_configured_planner(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"tabs": [{"label": "codex"}]}))
    (tmp_path / "gea.local.json").write_text(json.dumps({"agents": {"planner": "codex"}}))
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)


def _fake_cli(monkeypatch, output, code=0):
    monkeypatch.setattr(models.proc, "run", lambda cmd, timeout=30: (output, "", code))
    models._cache.clear()


def test_opencode_models_are_provider_slash_model_lines(monkeypatch):
    _fake_cli(monkeypatch, "opencode/big-pickle\nopencode-go/kimi-k2.7-code\nnoise line\n")
    assert [m.id for m in models.list_models("opencode")] == [
        "opencode/big-pickle",
        "opencode-go/kimi-k2.7-code",
    ]


def test_agy_models_skip_the_fetching_notice_and_keep_labels(monkeypatch):
    _fake_cli(
        monkeypatch, "Fetching available models...\ngemini-3.1-pro-high\tGemini 3.1 Pro (High)\n"
    )
    (model,) = models.list_models("agy")
    assert (model.id, model.label) == ("gemini-3.1-pro-high", "Gemini 3.1 Pro (High)")


def test_codex_models_only_the_listed_ones(monkeypatch):
    _fake_cli(
        monkeypatch,
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.5", "display_name": "GPT-5.5", "visibility": "list"},
                    {"slug": "hidden", "visibility": "hide"},
                ]
            }
        ),
    )
    assert [m.id for m in models.list_models("codex")] == ["gpt-5.5"]


def test_claude_lists_its_aliases_and_kimi_cannot_list(monkeypatch):
    models._cache.clear()
    assert [m.id for m in models.list_models("claude")][0] == "opusplan"
    assert models.list_models("kimi") is None


def test_a_failing_cli_yields_none_and_is_known_is_tri_state(monkeypatch):
    _fake_cli(monkeypatch, "", code=1)
    assert models.list_models("opencode") is None
    assert models.is_known("opencode", "x/y") is None
    _fake_cli(monkeypatch, "opencode/a\n")
    assert models.is_known("opencode", "opencode/a") is True
    assert models.is_known("opencode", "opencode/b") is False
    assert models.is_known("claude", "anything") is None
