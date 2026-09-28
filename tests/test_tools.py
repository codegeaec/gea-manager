from gea.setup import tools


def test_missing_mise_tools_reports_absent_ones(monkeypatch):
    def which(name):
        return None if name in ("rg", "jq") else "/usr/bin/" + name

    monkeypatch.setattr(tools.platform, "which", which)
    missing = tools.missing_mise_tools(["jq", "gh", "ripgrep"])
    assert set(missing) == {"jq", "ripgrep"}


def test_install_mise_tools_only_installs_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools.platform, "which", lambda name: "/usr/bin/x" if name == "jq" else None
    )
    monkeypatch.setattr(tools.proc, "run", lambda cmd, timeout=30: calls.append(cmd) or ("", "", 0))
    installed = tools.install_mise_tools(["jq", "gh"])
    assert installed == ["gh"]
    assert calls == [["mise", "use", "-g", "gh"]]


def test_ensure_mise_noop_when_present(monkeypatch):
    monkeypatch.setattr(tools.platform, "which", lambda name: "/usr/bin/mise")
    called = []
    monkeypatch.setattr(tools.proc, "run", lambda *a, **k: called.append(1))
    assert tools.ensure_mise() is False
    assert called == []


def test_ensure_system_packages_uses_apt_when_available(monkeypatch):
    calls = []
    monkeypatch.setattr(tools.platform, "has_apt", lambda: True)
    monkeypatch.setattr(tools.platform, "has_brew", lambda: False)
    monkeypatch.setattr(tools.platform, "which", lambda name: None)
    monkeypatch.setattr(tools.proc, "run", lambda cmd, timeout=30: calls.append(cmd) or ("", "", 0))
    installed = tools.ensure_system_packages()
    assert installed == tools.SYSTEM_PACKAGES_APT
    assert any(cmd[:2] == ["sudo", "apt-get"] for cmd in calls)
