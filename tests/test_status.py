from gea import status
from gea.agents import log, state
from gea.tasks import store


def test_status_shows_tasks_managed_panes_and_exhausted_pools(tmp_path, monkeypatch, capsys):
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    monkeypatch.chdir(tmp_path)
    store.create_task("Work", repo_root=tmp_path)
    log.append({"task_id": "TASK-001", "agent_id": "codex", "result": "done", "verify_ok": True})
    monkeypatch.setattr(
        status.herdr,
        "herdr_json",
        lambda cmd, timeout=15: (
            {"agents": [
                {"name": "builder-codex", "agent_status": "working"},
                {"name": "my-own-pane", "agent_status": "idle"},
                {"agent_status": "idle"},
            ]},
            None,
        ),
    )
    state.save({"codex": "2099-01-01T00:00:00+00:00"})
    assert status.run_status() == 0
    out = capsys.readouterr().out
    assert "TASK-001" in out and "codex done verify=True" in out
    assert "builder-codex" in out and "my-own-pane" not in out
    assert "codex" in out and "2099" in out
