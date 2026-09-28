from gea.setup import shadcn_setup


def test_review_mcp_servers_noop_when_none_found(monkeypatch, capsys):
    monkeypatch.setattr(shadcn_setup.shadcn, "detect_mcp_servers", lambda: [])
    shadcn_setup.review_mcp_servers(assume_yes=True)
    assert "no shadcn mcp" in capsys.readouterr().out.lower()


def test_review_mcp_servers_removes_when_assume_yes(monkeypatch):
    hit = shadcn_setup.shadcn.ShadcnMcpHit(
        location="Claude Code (user) (~/.claude.json)", key="shadcn"
    )
    monkeypatch.setattr(shadcn_setup.shadcn, "detect_mcp_servers", lambda: [hit])
    monkeypatch.setattr(shadcn_setup, "_backup_claude_config", lambda: None)
    removed = []
    monkeypatch.setattr(
        shadcn_setup.shadcn, "remove_from_claude_config", lambda key: removed.append(key) or True
    )
    shadcn_setup.review_mcp_servers(assume_yes=True)
    assert removed == ["shadcn"]
