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
