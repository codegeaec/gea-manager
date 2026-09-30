import subprocess

import pytest

from gea import config, handoff
from gea.agents import log
from gea.tasks import store


@pytest.fixture
def repo(tmp_path, monkeypatch):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"},"primary":"claude"}')
    git("add", ".")
    git("commit", "-qm", "init")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _task(repo, title, status, objective=""):
    path = store.create_task(title, repo_root=repo)
    text = path.read_text().replace("Status: planned", f"Status: {status}", 1)
    path.write_text(text.replace("## Objective\n", f"## Objective\n\n{objective}\n", 1))


def test_handoff_lists_only_in_flight_tasks(repo):
    _task(repo, "Working", "in-progress", "Ship the widget")
    _task(repo, "Waiting", "review")
    _task(repo, "Later", "planned")
    log.append({"task_id": "TASK-001", "agent_id": "codex", "result": "done", "verify_ok": True})
    text = handoff.build(repo)
    assert "TASK-001 - Working" in text and "Ship the widget" in text
    assert "codex -> done" in text and "TASK-002 - Waiting" in text
    assert "Later" not in text
    assert text.startswith("# Handoff")  # fixed prefix first


def test_handoff_excludes_closed_tasks(repo):
    _task(repo, "Done one", "review")
    store.close_task("TASK-001", repo_root=repo)
    assert "Done one" not in handoff.build(repo)


def test_handoff_without_target_only_writes_the_file(repo, capsys):
    assert handoff.run_handoff() == 0
    assert (repo / ".gea" / "HANDOFF.md").exists()
    assert "Paste into the new orchestrator" in capsys.readouterr().out


def test_handoff_to_starts_the_pane_and_switches_primary(repo, monkeypatch):
    calls = []
    monkeypatch.setattr(handoff.platform, "which", lambda n: "/x")
    monkeypatch.setattr(handoff.herdr, "start_agent_pane", lambda *a: calls.append(a) or "started")
    monkeypatch.setattr(handoff.herdr, "prompt_pane", lambda *a, **k: calls.append(a) or ("", 0))
    assert handoff.run_handoff(to="codex", assume_yes=True) == 0
    name = handoff.herdr.pane_name_for(repo, "orchestrator", "codex")
    assert calls[0][0] == name and name.endswith("-orchestrator-codex")
    assert calls[1][0] == name and "HANDOFF.md" in calls[1][1]
    assert config.agents(config.load_project(repo)).planner == "codex"
    assert log.read(kind="handoff")


def test_handoff_rejects_unknown_or_missing_cli(repo, monkeypatch):
    assert handoff.run_handoff(to="emacs") == 1
    monkeypatch.setattr(handoff.platform, "which", lambda n: None)
    assert handoff.run_handoff(to="codex") == 1
