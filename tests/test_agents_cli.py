import json

from gea.agents import cli as agents_cli


def _seed_profiles(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path))
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "builders": {
                    "profiles": [
                        {
                            "id": "codex", "cli": "codex", "model": None,
                            "pool": "codex", "priority": 11,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


def test_cmd_available_lists_non_exhausted(tmp_path, monkeypatch, capsys):
    _seed_profiles(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    code = agents_cli.cmd_available()
    out = capsys.readouterr().out
    assert code == 0
    assert "codex" in out


def test_cmd_reset_unknown_agent(tmp_path, monkeypatch, capsys):
    _seed_profiles(tmp_path, monkeypatch)
    code = agents_cli.cmd_reset("does-not-exist")
    assert code == 1
    assert "unknown agent" in capsys.readouterr().out


def test_refresh_detects_and_stores_profiles(monkeypatch, capsys):
    from gea.agents import cli as agents_cli
    from gea.agents import profiles

    monkeypatch.setattr(profiles.platform, "which", lambda n: "/x" if n == "codex" else None)
    assert agents_cli.cmd_refresh() == 0
    assert "codex" in capsys.readouterr().out
    assert [p.id for p in profiles.load_profiles()] == ["codex"]
