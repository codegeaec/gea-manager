import subprocess

import pytest

from gea import managed_block, manifest, uninstall
from gea.init import scaffold, wizard

MINE_AGENTS = "# Reglas de mi proyecto\n\n1. Nunca `any`.\n\n\tsangría  \n"
MINE_CLAUDE = "@AGENTS.md\n\n# CLAUDE.md\n\nNotas mías.\n"

KW = dict(
    lang="es", project_name="demo", pm="pnpm", commit_lang="es", docs_lang="es",
    verify_commands=["pnpm lint"], tasks_root_display="~/gea/projects/demo", has_shadcn=False,
)


def test_existing_agents_md_gets_only_a_block(tmp_path):
    (tmp_path / "AGENTS.md").write_text(MINE_AGENTS)
    assert scaffold.ensure_agents_md(tmp_path, **KW) == "updated"
    text = (tmp_path / "AGENTS.md").read_text()
    assert text.startswith(MINE_AGENTS)  # byte for byte
    assert "## Trabajo con gea" in text and "`pnpm lint`" in text
    assert scaffold.ensure_agents_md(tmp_path, **KW) == "unchanged"  # idempotent


def test_missing_agents_md_is_created_from_the_template(tmp_path):
    assert scaffold.ensure_agents_md(tmp_path, **KW) == "created"
    assert managed_block.START_MARKER not in (tmp_path / "AGENTS.md").read_text()


def test_existing_claude_md_imports_the_orchestrator_without_duplicating_agents_import(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(MINE_CLAUDE)
    assert scaffold.ensure_claude_md(tmp_path, "en", "demo", "x") == "updated"
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.startswith(MINE_CLAUDE) and "@.agents/orchestrator.md" in text
    assert text.count("@AGENTS.md") == 1
    (tmp_path / "CLAUDE.md").write_text("# no imports here\n")
    scaffold.ensure_claude_md(tmp_path, "en", "demo", "x")
    assert "@AGENTS.md" in (tmp_path / "CLAUDE.md").read_text()


def test_the_block_is_recorded_and_uninstall_removes_it_restoring_the_file(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_text(MINE_AGENTS)
    scaffold.ensure_agents_md(tmp_path, **KW)
    assert str(tmp_path / "AGENTS.md") in manifest.of_kind(manifest.KIND_INSTRUCTIONS)
    monkeypatch.setattr(uninstall.proc, "run_visible", lambda *a, **k: 0)
    assert uninstall.run_uninstall(assume_yes=True) == 0
    assert (tmp_path / "AGENTS.md").read_text() == MINE_AGENTS.rstrip("\n") + "\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(wizard.platform, "which", lambda n: "/x" if n == "claude" else None)
    monkeypatch.setattr(wizard, "load_profiles", lambda: [])
    monkeypatch.setattr(wizard, "refresh_and_save", lambda: [])
    return tmp_path


def test_full_init_on_an_existing_project_keeps_user_content_and_is_idempotent(repo):
    (repo / "AGENTS.md").write_text(MINE_AGENTS)
    (repo / "CLAUDE.md").write_text(MINE_CLAUDE)
    (repo / ".agents").mkdir()
    (repo / ".agents" / "convenciones-commits.md").write_text("mías")
    wizard.run_init(assume_yes=True, langs=("es", "es", "es"))
    snapshot = {p: p.read_text() for p in repo.rglob("*") if p.is_file() and ".git/" not in str(p)}
    assert (repo / "AGENTS.md").read_text().startswith(MINE_AGENTS)
    assert (repo / ".agents" / "convenciones-commits.md").read_text() == "mías"
    assert not (repo / ".agents" / "commit-conventions.md").exists()
    wizard.run_init(assume_yes=True, langs=("es", "es", "es"))
    again = {p: p.read_text() for p in repo.rglob("*") if p.is_file() and ".git/" not in str(p)}
    assert again == snapshot
