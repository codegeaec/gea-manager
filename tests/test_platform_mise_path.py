from gea import platform


def test_refresh_mise_shims_on_path_adds_default_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("MISE_DATA_DIR", raising=False)
    monkeypatch.setattr(platform.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("PATH", "/usr/bin")
    platform.refresh_mise_shims_on_path()
    expected_shims = str(tmp_path / ".local" / "share" / "mise" / "shims")
    assert platform.os.environ["PATH"].split(platform.os.pathsep)[0] == expected_shims


def test_refresh_mise_shims_on_path_respects_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MISE_DATA_DIR", str(tmp_path / "custom-mise"))
    monkeypatch.setenv("PATH", "/usr/bin")
    platform.refresh_mise_shims_on_path()
    expected_shims = str(tmp_path / "custom-mise" / "shims")
    assert expected_shims in platform.os.environ["PATH"].split(platform.os.pathsep)


def test_refresh_mise_shims_on_path_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("MISE_DATA_DIR", str(tmp_path / "mise"))
    monkeypatch.setenv("PATH", "/usr/bin")
    platform.refresh_mise_shims_on_path()
    first = platform.os.environ["PATH"]
    platform.refresh_mise_shims_on_path()
    assert platform.os.environ["PATH"] == first
