import json

from gea import verify


def test_run_verify_no_commands_configured(tmp_path, capsys):
    (tmp_path / "gea.json").write_text("{}", encoding="utf-8")
    code = verify.run_verify(tmp_path)
    assert code == 1
    assert "no verify commands" in capsys.readouterr().out.lower()


def test_run_verify_all_pass(tmp_path, monkeypatch):
    (tmp_path / "gea.json").write_text(json.dumps({"verify": ["true"]}), encoding="utf-8")
    monkeypatch.setattr(verify.proc, "run_streaming", lambda cmd, **kw: ("", "", 0))
    assert verify.run_verify(tmp_path) == 0


def test_run_verify_reports_failure(tmp_path, monkeypatch, capsys):
    (tmp_path / "gea.json").write_text(json.dumps({"verify": ["false"]}), encoding="utf-8")
    monkeypatch.setattr(verify.proc, "run_streaming", lambda cmd, **kw: ("boom", "", 1))
    code = verify.run_verify(tmp_path)
    assert code == 1
    assert "boom" in capsys.readouterr().out
