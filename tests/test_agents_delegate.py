import json

from gea.agents import delegate


def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "gea-home"))
    (tmp_path / "gea-home").mkdir(exist_ok=True)
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


notified: list = []


def _delegate_with_fakes(tmp_path, monkeypatch, start_status, prompt_result):
    from gea.tasks import store

    repo = _seed(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)
    store.create_task("Something", repo_root=repo)
    monkeypatch.setattr(delegate.checkpoint, "create", lambda *_: False)
    monkeypatch.setattr(delegate.herdr, "notify", lambda *a, **k: notified.append(a))
    monkeypatch.setattr(delegate.checkpoint, "changed_files", lambda *a: ["x.py"])
    monkeypatch.setattr(delegate.verify, "run_verify", lambda *a, **k: 0)
    monkeypatch.setattr(delegate.herdr, "start_builder_pane", lambda *a: start_status)
    monkeypatch.setattr(delegate.herdr, "prompt_result", lambda *a, **k: prompt_result)
    monkeypatch.setattr(delegate.herdr, "read_pane", lambda *a, **k: "last words")
    return delegate.delegate_task("TASK-001")


def test_delegate_logs_a_successful_attempt(tmp_path, monkeypatch):
    from gea.agents import log

    code = _delegate_with_fakes(tmp_path, monkeypatch, "started builder-codex", ("ok", 0, None))
    assert code == 0
    entry = log.last_for_task("TASK-001")
    assert entry["result"] == "done" and entry["agent_id"] == "codex" and entry["round"] == 1


def test_delegate_logs_blocked_start(tmp_path, monkeypatch):
    from gea.agents import log

    assert _delegate_with_fakes(tmp_path, monkeypatch, "BLOCKED builder-codex", ("", 0, None)) == 1
    assert log.last_for_task("TASK-001")["result"] == "blocked"


def test_delegate_timeout_is_logged_and_noted_in_the_task(tmp_path, monkeypatch):
    from gea.agents import log
    from gea.tasks import store

    code = _delegate_with_fakes(tmp_path, monkeypatch, "started builder-codex", ("", 1, "timeout"))
    assert code == 1
    assert log.last_for_task("TASK-001")["result"] == "timeout"
    notes = store.find_task_path("TASK-001", tmp_path / "repo").read_text(encoding="utf-8")
    assert "last words" in notes and "budget" in notes


def test_delegate_notifies_when_the_builder_finishes(tmp_path, monkeypatch):
    notified.clear()
    _delegate_with_fakes(tmp_path, monkeypatch, "started builder-codex", ("ok", 0, None))
    assert notified and notified[0][0] == "TASK-001: done"


def test_delegate_flags_files_outside_the_declared_scope(tmp_path, monkeypatch):
    from gea.agents import log
    from gea.tasks import store

    repo = _seed(tmp_path, monkeypatch)
    monkeypatch.chdir(repo)
    path = store.create_task("Scoped", repo_root=repo)
    path.write_text(path.read_text().replace("## Files\n", "## Files\n\n- `src/a.py`\n", 1))
    monkeypatch.setattr(delegate.checkpoint, "create", lambda *_: False)
    monkeypatch.setattr(delegate.checkpoint, "changed_files", lambda *_: ["src/a.py", "oops.py"])
    monkeypatch.setattr(delegate.herdr, "notify", lambda *a, **k: True)
    monkeypatch.setattr(delegate.herdr, "start_builder_pane", lambda *a: "started")
    monkeypatch.setattr(delegate.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    assert delegate.delegate_task("TASK-001") == 0
    assert log.last_for_task("TASK-001")["files_out_of_scope"] == 1
    assert "`oops.py`" in path.read_text()


def test_delegate_prints_a_compact_summary_not_the_raw_output(tmp_path, monkeypatch, capsys):
    from gea.agents import log

    _delegate_with_fakes(tmp_path, monkeypatch, "started builder-codex", ("RAW NOISE", 0, None))
    out = capsys.readouterr().out
    assert "RAW NOISE" not in out and "verify: passed" in out and "1 changed" in out
    assert log.last_for_task("TASK-001")["verify_ok"] is True


def test_reused_pane_gets_a_fresh_session_only_for_a_different_task(tmp_path, monkeypatch):
    from gea.agents import log

    cleared = []
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "gea-home"))  # same home _seed() uses
    monkeypatch.setattr(delegate.herdr, "clear_session", lambda *a: cleared.append(a) or True)
    log.append({"kind": "build", "task_id": "TASK-000", "agent_id": "codex"})
    reuse = "pane builder-codex already exists, reusing it"
    _delegate_with_fakes(tmp_path, monkeypatch, reuse, ("", 0, None))
    assert cleared == [("builder-codex", "codex")]

    cleared.clear()  # a correction round of the same task keeps the session
    monkeypatch.setattr(delegate.herdr, "start_builder_pane", lambda *a: "reused existing pane")
    delegate.delegate_task("TASK-001")
    assert cleared == []


def test_clear_session_only_for_known_clis(monkeypatch):
    from gea.agents import herdr

    sent = []
    monkeypatch.setattr(herdr, "prompt_result", lambda p, m, **k: sent.append(m) or ("", 0, None))
    monkeypatch.setattr(herdr.time, "sleep", lambda s: None)
    assert herdr.clear_session("p", "claude") is True and sent == ["/clear"]
    assert herdr.clear_session("p", "kimi") is False and sent == ["/clear"]
