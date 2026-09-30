import json

import pytest

from gea import config


def test_defaults_carry_schema_version_and_autonomy(tmp_path):
    data = config.load_project(tmp_path)
    assert data["schema_version"] == config.SCHEMA_VERSION
    assert data["autonomy"] == "balanced"
    assert config.load_global()["schema_version"] == config.SCHEMA_VERSION


def test_legacy_file_without_schema_version_still_loads(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"name": "x"}), encoding="utf-8")
    assert config.load_project(tmp_path)["schema_version"] == 1


def test_newer_schema_is_refused(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(config.ConfigError, match="newer"):
        config.load_project(tmp_path)


@pytest.mark.parametrize("bad", ["1", 0, True, None])
def test_invalid_schema_version_is_refused(tmp_path, bad):
    (tmp_path / "gea.json").write_text(json.dumps({"schema_version": bad}), encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)


def test_unknown_autonomy_is_refused(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"autonomy": "yolo"}), encoding="utf-8")
    with pytest.raises(config.ConfigError, match="autonomy"):
        config.load_project(tmp_path)


def test_dry_run_does_not_write(tmp_path):
    from gea import dryrun

    dryrun.enable(True)
    config.save_project(tmp_path, {"schema_version": 1})
    assert not (tmp_path / "gea.json").exists()


def _tabs(tmp_path, tabs, **extra):
    (tmp_path / "gea.json").write_text(json.dumps({"tabs": tabs, **extra}))
    return config.load_project(tmp_path)


def test_valid_tabs_load(tmp_path):
    tabs = [{"label": "web", "cwd": "apps/web", "command": "pnpm dev"}, {"label": "api"}]
    assert _tabs(tmp_path, tabs)["tabs"] == tabs
    assert config.load_project(tmp_path / "empty")["tabs"] == []


@pytest.mark.parametrize(
    "tabs",
    [
        "web",
        [{"cwd": "x"}],
        [{"label": " "}],
        [{"label": "terminal"}],
        [{"label": "claude"}],
        [{"label": "Web"}, {"label": "web"}],
        [{"label": "a", "cwd": "/etc"}],
        [{"label": "a", "cwd": "../other"}],
        [{"label": "a", "cwd": "x/../../y"}],
        [{"label": "a", "command": 3}],
    ],
)
def test_invalid_tabs_are_refused(tmp_path, tabs):
    with pytest.raises(config.ConfigError):
        _tabs(tmp_path, tabs)


def test_a_personal_tabs_list_replaces_the_shared_one_and_is_validated(tmp_path):
    (tmp_path / "gea.json").write_text(json.dumps({"tabs": [{"label": "web"}]}))
    (tmp_path / "gea.local.json").write_text(json.dumps({"tabs": [{"label": "mine"}]}))
    assert config.load_project(tmp_path)["tabs"] == [{"label": "mine"}]
    (tmp_path / "gea.local.json").write_text(json.dumps({"tabs": [{"label": "a", "cwd": "/x"}]}))
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)
