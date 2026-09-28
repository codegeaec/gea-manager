from gea import doctor


def test_run_doctor_flags_missing_tools(monkeypatch):
    def which(name):
        return None if name == "herdr" else "/usr/bin/x"

    monkeypatch.setattr(doctor.platform, "which", which)
    monkeypatch.setattr(doctor.shadcn, "detect_mcp_servers", lambda: [])
    result = doctor.run_doctor()
    assert "herdr" in result.missing_required
    assert not result.is_healthy


def test_run_doctor_healthy_when_everything_present(monkeypatch):
    monkeypatch.setattr(doctor.platform, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(doctor.shadcn, "detect_mcp_servers", lambda: [])
    result = doctor.run_doctor()
    assert result.is_healthy
    assert result.missing_required == []
    assert result.missing_optional == []
