import pytest

from gea import dryrun


@pytest.fixture(autouse=True)
def isolated_machine(tmp_path_factory, monkeypatch):
    """No test may read or write the real ~/gea or the real home."""
    home = tmp_path_factory.mktemp("machine")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GEA_HOME", str(home / "gea"))
    monkeypatch.setenv("GEA_LANG", "en")  # assertions read the English catalog
    dryrun.enable(False)
    yield
    dryrun.enable(False)
