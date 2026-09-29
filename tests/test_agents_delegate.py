import json

from gea.agents import delegate


def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "gea-home"))
    (tmp_path / "gea-home").mkdir()
    (tmp_path / "gea-home" / "config.json").write_text(
        json.dumps(
            {
                "builders": {
                    "profiles": [
                        {
                            "id": "codex", "cli": "codex", "model": None,
                            "pool": "codex", "priority": 11,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "gea.json").write_text('{"tasks": {"location": "repo"}}', encoding="utf-8")
    return repo


def test_delegate_task_not_found(tmp_path, monkeypatch, capsys):
    repo = _seed(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)
    code = delegate.delegate_task("TASK-999")
    assert code == 1
    assert "task not found" in capsys.readouterr().out.lower()


def test_delegate_task_no_agent_available(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "empty-gea-home"))
    repo = tmp_path / "repo2"
    repo.mkdir()
    (repo / "gea.json").write_text('{"tasks": {"location": "repo"}}', encoding="utf-8")
    monkeypatch.chdir(repo)
    from gea.tasks import store

    store.create_task("Something", repo_root=repo)
    code = delegate.delegate_task("TASK-001")
    assert code == 1


def _delegate_with_fakes(tmp_path, monkeypatch, start_status, prompt_result):
    from gea.tasks import store

    repo = _seed(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)
    store.create_task("Something", repo_root=repo)
    monkeypatch.setattr(delegate.checkpoint, "create", lambda *_: False)
    monkeypatch.setattr(delegate.herdr, "start_builder_pane", lambda *a: start_status)
    monkeypatch.setattr(delegate.herdr, "prompt_pane", lambda *a, **k: prompt_result)
    return delegate.delegate_task("TASK-001")


def test_delegate_logs_a_successful_attempt(tmp_path, monkeypatch):
    from gea.agents import log

    assert _delegate_with_fakes(tmp_path, monkeypatch, "started builder-codex", ("ok", 0)) == 0
    entry = log.last_for_task("TASK-001")
    assert entry["result"] == "done" and entry["agent_id"] == "codex" and entry["round"] == 1


def test_delegate_logs_blocked_start(tmp_path, monkeypatch):
    from gea.agents import log

    assert _delegate_with_fakes(tmp_path, monkeypatch, "BLOCKED builder-codex", ("", 0)) == 1
    assert log.last_for_task("TASK-001")["result"] == "blocked"
