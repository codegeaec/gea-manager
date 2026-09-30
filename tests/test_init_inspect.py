import json

from gea.init import inspect as inspect_mod
from gea.init import report, scaffold


def test_empty_repo_is_a_new_project(tmp_path):
    state = inspect_mod.inspect(tmp_path)
    assert not state.is_existing and not state.equivalents


def test_existing_files_are_detected_with_sizes(tmp_path):
    (tmp_path / "AGENTS.md").write_text("x" * 4 * 2100)
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md")
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "convenciones-commits.md").write_text("c")
    (tmp_path / ".agents" / "gotchas.md").write_text("g")
    state = inspect_mod.inspect(tmp_path)
    assert state.is_existing and state.agents_md_oversized
    assert state.equivalents == {"commit-conventions.md": "convenciones-commits.md"}
    # an exact-name file is not an "equivalent" of itself — write_if_missing handles it
    assert "gotchas.md" not in state.equivalents


def test_only_project_level_shadcn_mcp_counts(tmp_path):
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"shadcn": {"command": "x"}}}))
    assert len(inspect_mod.inspect(tmp_path).shadcn_mcp) == 1


def test_scaffold_does_not_duplicate_an_existing_equivalent(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "convenciones-commits.md").write_text("mine")
    written = scaffold.write_agents_dir(tmp_path, "es", "demo", "es", False, "x")
    assert ".agents/commit-conventions.md" not in written
    assert not (tmp_path / ".agents" / "commit-conventions.md").exists()
    assert ".agents/orchestrator.md" in written  # gea's own files still arrive


def test_report_prints_warnings_and_actions(tmp_path, capsys):
    (tmp_path / "AGENTS.md").write_text("x" * 4 * 2100)
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "convenciones-commits.md").write_text("c")
    report.print_report(inspect_mod.inspect(tmp_path))
    out = capsys.readouterr().out
    assert "existing project" in out and "kept as is" in out
    assert "convenciones-commits.md" in out and "2000" in out
