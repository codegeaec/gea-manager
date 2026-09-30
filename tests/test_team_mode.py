import json

from gea import config
from gea.init import scaffold


def test_local_file_wins_over_shared_with_deep_merge(tmp_path):
    (tmp_path / "gea.json").write_text(
        json.dumps({"primary": "claude", "builders": {"mode": "ask", "ponytail": True}})
    )
    (tmp_path / "gea.local.json").write_text(
        json.dumps({"primary": "codex", "builders": {"mode": "auto"}})
    )
    cfg = config.load_project(tmp_path)
    assert cfg["primary"] == "codex"
    assert cfg["builders"] == {"mode": "auto", "ponytail": True}


def test_save_splits_policy_from_personal_choices(tmp_path):
    data = config.load_project(tmp_path)
    planner = {"planner": "codex", "plannerModel": "gpt-5.5"}
    data.update(name="demo", agents=planner, verify=["pytest"])
    data["builders"] = {"mode": "auto", "ponytail": True}
    config.save_project(tmp_path, data)

    shared = json.loads((tmp_path / "gea.json").read_text())
    local = json.loads((tmp_path / "gea.local.json").read_text())
    assert "agents" not in shared and "primary" not in shared
    assert shared["verify"] == ["pytest"] and shared["builders"]["ponytail"] is True
    assert local["agents"] == {"planner": "codex", "plannerModel": "gpt-5.5"}
    assert local["builders"] == {"mode": "auto"}
    assert config.load_project(tmp_path) == data | {"schema_version": 1} | {}


def test_no_local_file_when_nothing_is_personal(tmp_path):
    config.save_project(tmp_path, config.load_project(tmp_path))
    assert not (tmp_path / "gea.local.json").exists()


def test_gitignore_now_ignores_local_not_shared_and_migration_is_backed_up(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules\ngea.json\n")
    scaffold.update_gitignore(tmp_path, "repo")
    assert "gea.local.json" in (tmp_path / ".gitignore").read_text().splitlines()
    assert scaffold.gitignore_has_gea_json(tmp_path)
    assert scaffold.stop_ignoring_gea_json(tmp_path)
    assert "gea.json" not in (tmp_path / ".gitignore").read_text().splitlines()
    assert "gea.json" in (tmp_path / ".gitignore.bak").read_text().splitlines()
    assert not scaffold.stop_ignoring_gea_json(tmp_path)
