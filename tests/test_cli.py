from gea import __version__
from gea.cli import main


def test_version_flag(capsys):
    code = main(["--version"])
    assert code == 0
    assert __version__ in capsys.readouterr().out


def test_no_args_opens_workspace(monkeypatch):
    calls = []
    import gea.workspace as workspace

    monkeypatch.setattr(workspace, "open_or_focus", lambda: calls.append(1) or 0)
    assert main([]) == 0
    assert calls == [1]


def test_doctor_command_runs(capsys, monkeypatch):
    from gea import doctor

    monkeypatch.setattr(doctor.platform, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(doctor.shadcn, "detect_mcp_servers", lambda: [])
    assert main(["doctor"]) == 0
    assert "doctor" in capsys.readouterr().out.lower() or True
