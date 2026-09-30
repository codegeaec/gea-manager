import json

import pytest

from gea import config
from gea.agents import delegate, herdr, review


def test_created_by_gea_excludes_panes_the_user_opened():
    assert herdr.created_by_gea("started cot-builder-x (codex)")
    assert herdr.created_by_gea("pane cot-builder-x already exists, reusing it")
    assert not herdr.created_by_gea("reused existing pane as cot-builder-x")
    assert not herdr.created_by_gea("BLOCKED cot-builder-x — waiting")


def _live(monkeypatch, pane_id="w1:p9"):
    monkeypatch.setenv("HERDR_ENV", "1")
    calls = []

    def fake(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["agent", "get"]:
            return {"agent": {"pane_id": pane_id}}, None
        return {}, None

    monkeypatch.setattr(herdr, "herdr_json", fake)
    return calls


def test_close_agent_pane_closes_the_hosting_pane(monkeypatch):
    calls = _live(monkeypatch)
    assert herdr.close_agent_pane("cot-builder-x") is True
    assert ["pane", "close", "w1:p9"] in calls


def test_the_callers_own_pane_is_never_closed(monkeypatch):
    calls = _live(monkeypatch, pane_id="w1:p1")
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p1")
    assert herdr.close_agent_pane("x") is False
    assert not any(c[:2] == ["pane", "close"] for c in calls)


def test_nothing_is_touched_outside_herdr(monkeypatch):
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.setattr(herdr, "herdr_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert herdr.close_agent_pane("x") is False


@pytest.mark.parametrize(
    ("cfg", "status", "verified", "closes"),
    [
        ({}, "started cot-builder-x", True, True),  # default policy: on-success
        ({"builders": {"close": "on-success"}}, "started cot-builder-x", True, True),
        ({"builders": {"close": "on-success"}}, "started cot-builder-x", False, False),
        ({"builders": {"close": "never"}}, "started cot-builder-x", True, False),
        ({}, "reused existing pane as cot-builder-x", True, False),  # the user's own pane
        ({}, "pane cot-builder-x already exists, reusing it", True, True),
    ],
)
def test_close_policy(monkeypatch, cfg, status, verified, closes):
    closed = []
    monkeypatch.setattr(delegate.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    assert delegate.close_finished_pane(cfg, "cot-builder-x", status, verified) is closes
    assert closed == (["cot-builder-x"] if closes else [])


def test_close_policy_must_be_a_known_value(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"builders": {"close": "sometimes"}}))
    with pytest.raises(config.ConfigError, match="builders.close"):
        config.load_project(tmp_path)
    (tmp_path / "gea.json").write_text(json.dumps({"builders": {"close": "never"}}))
    assert config.load_project(tmp_path)["builders"]["close"] == "never"


def test_delegate_closes_the_pane_after_a_verified_run_and_keeps_it_when_verify_fails(
    tmp_path, monkeypatch
):
    from tests.test_agents_delegate import _delegate_with_fakes

    closed = []
    monkeypatch.setattr(delegate.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    _delegate_with_fakes(tmp_path, monkeypatch, "started x", ("", 0, None))
    assert len(closed) == 1 and closed[0].endswith("-builder-codex")

    closed.clear()
    monkeypatch.setattr(delegate.verify, "run_verify", lambda *a, **k: 1)
    monkeypatch.setattr(delegate.herdr, "start_agent_pane", lambda *a: "started x")
    delegate.delegate_task("TASK-001")
    assert closed == []  # failing run: left open to inspect


def test_review_closes_its_reviewer_pane_too(tmp_path, monkeypatch):
    from gea.agents import log
    from tests.test_review import _seed

    _seed(tmp_path, monkeypatch)
    log.append({"kind": "build", "task_id": "TASK-001", "agent_id": "a", "pool": "a"})
    closed = []
    monkeypatch.setattr(review.herdr, "start_builder_pane", lambda *a: "started x")
    monkeypatch.setattr(review.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    monkeypatch.setattr(review.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    monkeypatch.setattr(review.review_pack, "run_review_pack", lambda *_: 0)
    assert review.review_task("TASK-001") == 0
    assert len(closed) == 1 and closed[0].endswith("-builder-b")
