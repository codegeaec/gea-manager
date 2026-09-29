from gea import paths
from gea.agents import log


def test_append_and_filter():
    log.append({"task_id": "TASK-001", "agent_id": "a", "result": "done"})
    log.append({"task_id": "TASK-002", "agent_id": "b", "result": "error"})
    assert [e["agent_id"] for e in log.read(task_id="TASK-001")] == ["a"]
    assert log.last_for_task("TASK-002")["result"] == "error"
    assert "ts" in log.read()[0]


def test_read_skips_corrupt_lines():
    log.append({"task_id": "TASK-001"})
    with paths.delegations_log_path().open("a") as f:
        f.write("not json\n[1]\n")
    assert len(log.read()) == 1


def test_missing_log_is_empty():
    assert log.read() == [] and log.last_for_task("x") is None
