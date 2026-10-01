import json
import os
import sys

from gea.agents import notify
from gea.tasks import store


def _spec(tmp_path, task_path, deadline_s=30):
    import time

    return {
        "project": "repo", "task_id": "TASK-001", "task_paths": [str(task_path)],
        "pane": "rep-builder", "target": "w1:p1", "deadline": time.time() + deadline_s,
    }


def _register(spec):
    path = notify._state_path(spec["project"], spec["task_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    return path


def _task(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "gea.json").write_text('{"tasks": {"location": "repo"}}', encoding="utf-8")
    return store.create_task("Something", repo_root=repo)


def test_notifies_once_when_task_reaches_review(tmp_path, monkeypatch):
    task = _task(tmp_path)
    spec = _spec(tmp_path, task)
    state = _register(spec)
    sent = []
    monkeypatch.setattr(notify.herdr, "agent_alive", lambda _p: True)
    monkeypatch.setattr(
        notify.herdr,
        "prompt_result",
        lambda to, msg, wait: sent.append((to, msg, wait)) or ("", 0, None),
    )
    polls = iter([None, "review"])

    def fake_sleep(_s):
        status = next(polls)
        if status:
            store.set_status("TASK-001", status, tmp_path / "repo")

    monkeypatch.setattr(notify.time, "sleep", fake_sleep)
    assert notify.watch(spec) == "review"
    assert sent == [("w1:p1", "TASK-001 finished (review). Run gea review-pack TASK-001", False)]
    assert not state.exists()  # one notice per run


def test_notifies_crashed_when_builder_pane_dies(tmp_path, monkeypatch):
    task = _task(tmp_path)
    spec = _spec(tmp_path, task)
    _register(spec)
    sent = []
    monkeypatch.setattr(notify.herdr, "agent_alive", lambda _p: False)
    monkeypatch.setattr(
        notify.herdr, "prompt_result", lambda to, msg, wait: sent.append(msg) or ("", 0, None)
    )
    monkeypatch.setattr(notify.time, "sleep", lambda _s: None)
    assert notify.watch(spec) == "crashed"
    assert "(crashed)" in sent[0]


def test_cancelled_watcher_sends_nothing(tmp_path, monkeypatch):
    task = _task(tmp_path)
    spec = _spec(tmp_path, task)
    state = _register(spec)
    sent = []
    monkeypatch.setattr(notify.herdr, "agent_alive", lambda _p: False)
    monkeypatch.setattr(
        notify.herdr, "prompt_result", lambda *a, **k: sent.append(a) or ("", 0, None)
    )
    monkeypatch.setattr(notify.time, "sleep", lambda _s: state.unlink())
    assert notify.watch(spec) is None
    assert sent == []


def test_status_already_review_does_not_fire(tmp_path, monkeypatch):
    task = _task(tmp_path)
    store.set_status("TASK-001", "review", tmp_path / "repo")
    spec = _spec(tmp_path, task, deadline_s=0)
    _register(spec)
    assert notify._outcome(spec["task_paths"], notify._statuses(spec["task_paths"])) is None


def test_start_needs_herdr(tmp_path):
    assert notify.start("TASK-001", tmp_path / "t.md", tmp_path, "p", None, 60) is False


def test_start_spawns_detached_watcher_and_stop_cancels(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p1")
    launched = []

    class FakeProc:
        pid = os.getpid()

    monkeypatch.setattr(
        notify.subprocess, "Popen", lambda cmd, **kw: launched.append((cmd, kw)) or FakeProc()
    )
    assert notify.start("TASK-001", tmp_path / "t.md", tmp_path, "pane", None, 60)
    cmd, kw = launched[0]
    assert cmd[:3] == [sys.executable, "-m", "gea.agents.notify"]
    assert kw["start_new_session"] is True
    state = notify._state_path(tmp_path.name, "TASK-001")
    assert state.exists()
    notify.stop(tmp_path.name, "TASK-001")  # our pid is not a watcher: only the file goes
    assert not state.exists()
