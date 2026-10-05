import json

from gea import config


def test_load_global_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "gea"))
    data = config.load_global()
    assert data["ui_lang"] == "es"
    assert data["builders"]["mode"] == "ask"


def test_save_and_reload_global(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "gea"))
    data = config.load_global()
    data["ui_lang"] = "en"
    config.save_global(data)
    assert config.load_global()["ui_lang"] == "en"


def test_load_project_defaults(tmp_path):
    data = config.load_project(tmp_path)
    assert data["tasks"]["location"] == "home"
    assert data["lang"]["commits"] == "es"


def test_load_project_merges_existing_file(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"lang": {"commits": "en"}}), encoding="utf-8")
    data = config.load_project(tmp_path)
    assert data["lang"] == {"commits": "en"}
    assert data["tasks"]["location"] == "home"


def test_invalid_workflow_rejected(tmp_path):
    import pytest

    from gea import config

    (tmp_path / "gea.json").write_text('{"schema_version": 1, "workflow": "x"}')
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)
