import json

from gea import paths
from gea.agents import delegate, exhaustion, herdr, log, profiles, state
from gea.tasks import store

QUOTA = """working on it...
⚠ Individual quota reached. Please upgrade your subscription to increase your
limits. Resets in 70h21m6s.
Error ID: 75bb5111-be26-4d18-a100-b10ca3a0589e-7
"""


def _profiles(*pools):
    return [
        {"id": p, "cli": p, "model": None, "pool": p, "priority": i} for i, p in enumerate(pools)
    ]


def _setup(tmp_path, monkeypatch, pools=("codex", "opencode")):
    paths.gea_home().mkdir(parents=True, exist_ok=True)
    paths.global_config_path().write_text(json.dumps({"builders": {"profiles": _profiles(*pools)}}))
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    monkeypatch.chdir(tmp_path)
    return store.create_task("t", repo_root=tmp_path)


def _agent():
    return profiles.AgentProfile("codex", "codex", None, "codex", 0)


def test_the_real_quota_message_marks_the_pool_closes_the_pane_and_suggests_another(
    tmp_path, monkeypatch, capsys
):
    _setup(tmp_path, monkeypatch)
    closed = []
    monkeypatch.setattr(exhaustion.herdr, "read_pane", lambda *a, **k: QUOTA)
    monkeypatch.setattr(exhaustion.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    assert exhaustion.check_exhausted(
        "cot-builder-codex", _agent(), tmp_path, "started x", "gea delegate T --agent {agent}"
    )
    until = state.parse_iso(state.load()["codex"])
    hours = (until - state.now()).total_seconds() / 3600
    assert 70.2 < hours < 70.5  # "Resets in 70h21m6s"
    assert closed == ["cot-builder-codex"]
    out = capsys.readouterr().out
    assert "gea delegate T --agent opencode" in out
    assert profiles.pick_agent(repo_root=tmp_path).id == "opencode"  # codex now skipped


def test_no_other_agent_says_so(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, pools=("codex",))
    monkeypatch.setattr(exhaustion.herdr, "read_pane", lambda *a, **k: QUOTA)
    monkeypatch.setattr(exhaustion.herdr, "close_agent_pane", lambda n: True)
    assert exhaustion.check_exhausted("p", _agent(), tmp_path, "started x", "cmd {agent}")
    assert "no other agent" in capsys.readouterr().out.lower()


def test_a_pane_the_user_opened_is_not_closed_and_normal_output_is_not_exhaustion(
    tmp_path, monkeypatch
):
    _setup(tmp_path, monkeypatch)
    closed = []
    monkeypatch.setattr(exhaustion.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    monkeypatch.setattr(exhaustion.herdr, "read_pane", lambda *a, **k: QUOTA)
    exhaustion.check_exhausted("p", _agent(), tmp_path, "reused existing pane as p", "x {agent}")
    assert closed == []  # marked exhausted, but the user's pane stays
    monkeypatch.setattr(exhaustion.herdr, "read_pane", lambda *a, **k: "all good\nTests pass\n")
    assert not exhaustion.check_exhausted("p", _agent(), tmp_path, "started x", "x {agent}")


def _delegate(tmp_path, monkeypatch, pane_text, changed, verify_rc=0, prompt=("", 0, None)):
    task = _setup(tmp_path, monkeypatch)
    task.write_text(task.read_text().replace("## Files\n", "## Files\n\n- `a.py`\n", 1))
    monkeypatch.setattr(delegate.checkpoint, "create", lambda *_: False)
    monkeypatch.setattr(delegate.checkpoint, "changed_files", lambda *a: changed)
    monkeypatch.setattr(delegate.herdr, "start_agent_pane", lambda *a: "started x")
    monkeypatch.setattr(delegate.herdr, "notify", lambda *a, **k: True)
    monkeypatch.setattr(delegate.herdr, "prompt_result", lambda *a, **k: prompt)
    monkeypatch.setattr(delegate.verify, "run_verify", lambda *a, **k: verify_rc)
    monkeypatch.setattr(exhaustion.herdr, "read_pane", lambda *a, **k: pane_text)
    closed = []
    monkeypatch.setattr(exhaustion.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    monkeypatch.setattr(delegate.herdr, "close_agent_pane", lambda n: closed.append(n) or True)
    return delegate.delegate_task("TASK-001"), closed


def test_delegate_recognises_a_quota_stop_that_looked_like_done(tmp_path, monkeypatch):
    rc, closed = _delegate(tmp_path, monkeypatch, QUOTA, changed=[])
    assert rc == 1 and len(closed) == 1
    assert log.last_for_task("TASK-001")["result"] == "exhausted"
    assert "codex" in state.load()


def test_delegate_recognises_quota_when_herdr_reports_an_error(tmp_path, monkeypatch):
    rc, _ = _delegate(tmp_path, monkeypatch, QUOTA, changed=["a.py"], prompt=("", 1, "unknown"))
    assert rc == 1 and log.last_for_task("TASK-001")["result"] == "exhausted"


def test_a_verified_run_with_changes_never_reads_the_pane(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("pane must not be read on a good run")

    monkeypatch.setattr(exhaustion.herdr, "read_pane", boom)
    task = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(delegate.checkpoint, "create", lambda *_: False)
    monkeypatch.setattr(delegate.checkpoint, "changed_files", lambda *a: ["a.py"])
    monkeypatch.setattr(delegate.herdr, "start_agent_pane", lambda *a: "started x")
    monkeypatch.setattr(delegate.herdr, "notify", lambda *a, **k: True)
    monkeypatch.setattr(delegate.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    monkeypatch.setattr(delegate.verify, "run_verify", lambda *a, **k: 0)
    monkeypatch.setattr(delegate.herdr, "close_agent_pane", lambda n: True)
    assert task and delegate.delegate_task("TASK-001") == 0
    assert log.last_for_task("TASK-001")["result"] == "done"


def test_a_failed_run_without_a_quota_message_is_not_marked_exhausted(tmp_path, monkeypatch):
    rc, closed = _delegate(tmp_path, monkeypatch, "tests failed\n", changed=["a.py"], verify_rc=1)
    assert rc == 0 and state.load() == {}
    assert closed == []  # failed verify keeps the pane for inspection


def test_read_pane_is_a_no_op_outside_herdr(monkeypatch):
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.setattr(herdr.proc, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert herdr.read_pane("x") == ""


def test_review_stuck_on_a_quota_message_is_reported_as_exhausted(tmp_path, monkeypatch):
    from gea.agents import review

    _setup(tmp_path, monkeypatch, pools=("codex", "opencode"))
    log.append({"kind": "build", "task_id": "TASK-001", "agent_id": "opencode", "pool": "opencode"})
    monkeypatch.setattr(review.herdr, "start_builder_pane", lambda *a: "started x")
    monkeypatch.setattr(review.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    monkeypatch.setattr(review.review_pack, "run_review_pack", lambda *_: 0)  # writes no findings
    monkeypatch.setattr(exhaustion.herdr, "read_pane", lambda *a, **k: QUOTA)
    monkeypatch.setattr(exhaustion.herdr, "close_agent_pane", lambda n: True)
    assert review.review_task("TASK-001") == 1
    assert log.last_for_task("TASK-001")["result"] == "exhausted" and "codex" in state.load()
