import argparse
import json

from gea.tasks import commands, store


def _args(**kw):
    base = dict(task_command="new", title=None, type=None, from_issue=None)
    return argparse.Namespace(**(base | kw))


def _repo(tmp_path, monkeypatch):
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    monkeypatch.chdir(tmp_path)


def test_task_is_seeded_from_the_issue(tmp_path, monkeypatch, capsys):
    _repo(tmp_path, monkeypatch)
    payload = json.dumps({"title": "Crash on save", "body": "Steps: click save"})
    monkeypatch.setattr(commands_proc(), "run", lambda cmd, timeout=30: (payload, "", 0))
    assert commands.dispatch_task(_args(from_issue="12", type="bugfix")) == 0
    text = store.find_task_path("TASK-001").read_text()
    assert "Crash on save" in text.splitlines()[0] and "Steps: click save" in text
    assert text.index("From issue #12") < text.index("## Expected vs Actual")  # in Symptom


def test_explicit_title_wins_over_the_issue_title(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    payload = json.dumps({"title": "Issue title", "body": ""})
    monkeypatch.setattr(commands_proc(), "run", lambda cmd, timeout=30: (payload, "", 0))
    commands.dispatch_task(_args(from_issue="3", title="Mine"))
    assert "Mine" in store.find_task_path("TASK-001").read_text().splitlines()[0]


def test_failed_gh_creates_nothing(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    monkeypatch.setattr(commands_proc(), "run", lambda cmd, timeout=30: ("", "not found", 1))
    assert commands.dispatch_task(_args(from_issue="9")) == 1
    assert store.find_task_path("TASK-001") is None


def test_title_or_issue_is_required(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    assert commands.dispatch_task(_args()) == 1


def commands_proc():
    from gea import proc

    return proc
