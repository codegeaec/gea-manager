from gea import platform


def test_which_finds_tools_in_the_mise_shims_even_when_not_on_path(monkeypatch, tmp_path):
    shims = tmp_path / "shims"
    shims.mkdir()
    tool = shims / "mytool"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    monkeypatch.setenv("MISE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PATH", "/nonexistent")
    assert platform.which("mytool") == str(tool)
