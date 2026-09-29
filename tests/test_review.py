import json

from gea import paths
from gea.agents import log, profiles, review
from gea.tasks import store


def _profiles(*pools):
    return [
        {"id": p, "cli": p, "model": None, "pool": p, "priority": i}
        for i, p in enumerate(pools)
    ]


def _seed(tmp_path, monkeypatch, pools=("a", "b")):
    paths.gea_home().mkdir(parents=True)
    cfg = {"builders": {"profiles": _profiles(*pools)}}
    paths.global_config_path().write_text(json.dumps(cfg))
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    monkeypatch.chdir(tmp_path)
    return store.create_task("t", repo_root=tmp_path)


def test_pick_agent_excludes_pools_and_honors_allow(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, ("a", "b", "c"))
    assert profiles.pick_agent().id == "a"
    assert profiles.pick_agent(exclude_pools=["a"]).id == "b"
    assert profiles.pick_agent("a", exclude_pools=["a"]) is None
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"},"builders":{"allow":["c"]}}')
    assert profiles.pick_agent().id == "c"


def test_review_uses_a_different_pool_than_the_builder(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    log.append({"kind": "build", "task_id": "TASK-001", "agent_id": "a", "pool": "a"})
    started = []
    monkeypatch.setattr(
        review.herdr, "start_builder_pane", lambda id_, *a: started.append(id_) or "started"
    )
    monkeypatch.setattr(review.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    monkeypatch.setattr(review.review_pack, "run_review_pack", lambda *_: 0)
    assert review.review_task("TASK-001") == 0
    assert started == ["b"]
    assert log.last_for_task("TASK-001")["kind"] == "review"


def test_review_without_another_agent_fails_cleanly(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, ("a",))
    log.append({"kind": "build", "task_id": "TASK-001", "agent_id": "a", "pool": "a"})
    assert review.review_task("TASK-001") == 1


def _builds(agent, tier, ok, n):
    for _ in range(n):
        log.append(
            {"kind": "build", "agent_id": agent, "tier": tier, "result": "done", "verify_ok": ok}
        )


def test_tier_ranking_demotes_a_proven_bad_agent(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, ("a", "b"))
    assert profiles.pick_agent(tier="L").id == "a"  # no history: priority order
    _builds("a", "L", False, 5)
    _builds("b", "L", True, 5)
    assert profiles.pick_agent(tier="L").id == "b"
    assert profiles.pick_agent(tier="S").id == "a"  # history is per tier


def test_tier_ranking_ignores_too_little_history(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, ("a", "b"))
    _builds("a", "L", False, 4)
    assert profiles.pick_agent(tier="L").id == "a"


def test_forced_tier_list_restricts_and_orders(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch, ("a", "b", "c"))
    (tmp_path / "gea.json").write_text(
        '{"tasks":{"location":"repo"},"builders":{"tiers":{"L":["c","b"]}}}'
    )
    assert profiles.pick_agent(tier="L").id == "c"
    assert profiles.pick_agent(tier="M").id == "a"
