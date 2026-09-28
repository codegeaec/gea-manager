import json

from gea import shadcn


def test_detect_mcp_servers_finds_shadcn_in_claude_config(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(
        json.dumps({"mcpServers": {"shadcn": {"command": "npx", "args": ["shadcn-mcp"]}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(shadcn.paths, "home", lambda: tmp_path)
    hits = shadcn.detect_mcp_servers()
    assert any("Claude Code" in h.location for h in hits)


def test_detect_mcp_servers_ignores_unrelated_entries(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(
        json.dumps({"mcpServers": {"figma": {"command": "npx", "args": ["figma-mcp"]}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(shadcn.paths, "home", lambda: tmp_path)
    assert shadcn.detect_mcp_servers() == []


def test_detect_mcp_servers_checks_project_mcp_json(tmp_path, monkeypatch):
    monkeypatch.setattr(shadcn.paths, "home", lambda: tmp_path)
    project = tmp_path / "myproject"
    project.mkdir()
    (project / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"shadcn-ui": {"command": "shadcn"}}}), encoding="utf-8"
    )
    hits = shadcn.detect_mcp_servers(project_root=project)
    assert any("project .mcp.json" in h.location for h in hits)


def test_remove_from_claude_config(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(
        json.dumps({"mcpServers": {"shadcn": {"command": "npx"}}}), encoding="utf-8"
    )
    monkeypatch.setattr(shadcn.paths, "home", lambda: tmp_path)
    assert shadcn.remove_from_claude_config("shadcn") is True
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    assert "shadcn" not in data["mcpServers"]
