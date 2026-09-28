from gea.setup import agents_install


def test_detected_agents_filters_by_which(monkeypatch):
    monkeypatch.setattr(
        agents_install.platform, "which", lambda name: "/x" if name == "claude" else None
    )
    detected = agents_install.detected_agents()
    assert [a.id for a in detected] == ["claude"]


def test_install_agent_skips_if_present(monkeypatch):
    monkeypatch.setattr(agents_install.platform, "which", lambda name: "/x")
    called = []
    monkeypatch.setattr(agents_install.proc, "run_visible", lambda *a, **k: called.append(1))
    agent = agents_install.AGENT_CLIS[0]
    assert agents_install.install_agent(agent) is False
    assert called == []


def test_install_herdr_integrations_only_for_agents_that_need_it(monkeypatch):
    calls = []
    monkeypatch.setattr(
        agents_install.proc, "run_visible", lambda cmd, timeout=30: calls.append(cmd) or 0
    )
    agents = [a for a in agents_install.AGENT_CLIS if a.id in ("claude", "opencode")]
    targets = agents_install.install_herdr_integrations(agents)
    assert targets == ["opencode"]
    assert calls == [["herdr", "integration", "install", "opencode"]]


def test_rtk_init_for_calls_base_and_per_agent_flags(monkeypatch):
    calls = []
    monkeypatch.setattr(
        agents_install.proc, "run_visible", lambda cmd, timeout=30: calls.append(cmd) or 0
    )
    agents = [a for a in agents_install.AGENT_CLIS if a.id == "codex"]
    agents_install.rtk_init_for(agents)
    assert ["rtk", "init", "-g", "--auto-patch"] in calls
    assert ["rtk", "init", "-g", "--auto-patch", "--codex"] in calls
