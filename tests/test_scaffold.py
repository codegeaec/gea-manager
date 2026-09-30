import json

from gea.init import scaffold


def test_write_agents_md_creates_file_with_substitutions(tmp_path):
    changed = scaffold.write_agents_md(
        tmp_path,
        lang="en",
        project_name="demo",
        pm="pnpm",
        commit_lang="en",
        docs_lang="en",
        verify_commands=["pnpm lint"],
        tasks_root_display="~/gea/projects/demo",
        has_shadcn=False,
    )
    assert changed is True
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "demo" in content
    assert "pnpm" in content
    assert "pnpm lint" in content
    assert "shadcn" not in content.lower()


def test_write_agents_md_includes_shadcn_section_when_present(tmp_path):
    scaffold.write_agents_md(
        tmp_path,
        lang="es",
        project_name="demo",
        pm="pnpm",
        commit_lang="es",
        docs_lang="es",
        verify_commands=[],
        tasks_root_display="~/gea/projects/demo",
        has_shadcn=True,
    )
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "shadcn" in content.lower()
    assert "pnpm dlx shadcn" in content


def test_write_agents_md_never_overwrites(tmp_path):
    (tmp_path / "AGENTS.md").write_text("custom content", encoding="utf-8")
    changed = scaffold.write_agents_md(
        tmp_path,
        lang="en",
        project_name="demo",
        pm="npm",
        commit_lang="en",
        docs_lang="en",
        verify_commands=[],
        tasks_root_display="x",
        has_shadcn=False,
    )
    assert changed is False
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "custom content"


def test_write_agents_dir_writes_all_files(tmp_path):
    written = scaffold.write_agents_dir(tmp_path, "en", "demo", "en", True, "~/gea/projects/demo")
    assert set(written) == {
        ".agents/README.md",
        ".agents/commit-conventions.md",
        ".agents/gotchas.md",
        ".agents/builder.md",
        ".agents/orchestrator.md",
        ".agents/gea.md",
    }
    builder = (tmp_path / ".agents" / "builder.md").read_text(encoding="utf-8")
    assert "ponytail" in builder.lower()


def test_write_agents_dir_without_ponytail(tmp_path):
    scaffold.write_agents_dir(tmp_path, "en", "demo", "en", False, "x")
    builder = (tmp_path / ".agents" / "builder.md").read_text(encoding="utf-8")
    assert "ponytail" not in builder.lower()


def test_write_docs(tmp_path):
    written = scaffold.write_docs(tmp_path, "es", "demo")
    assert "docs/INDEX.md" in written
    assert "docs/00-vision-producto.md" in written
    assert "docs/adr/0000-template.md" in written


def test_merge_claude_settings_creates_new_file(tmp_path):
    assert scaffold.merge_claude_settings(tmp_path) is True
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert data["attribution"]["sessionUrl"] is False


def test_merge_claude_settings_preserves_existing_keys(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"model": "opusplan"}), encoding="utf-8")
    changed = scaffold.merge_claude_settings(tmp_path)
    assert changed is True
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["model"] == "opusplan"
    assert "attribution" in data


def test_merge_claude_settings_noop_if_attribution_exists(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"attribution": {"commit": "custom"}}), encoding="utf-8")
    assert scaffold.merge_claude_settings(tmp_path) is False


def test_update_gitignore_adds_gea_local_json_and_gea_dir_for_home(tmp_path):
    scaffold.update_gitignore(tmp_path, "home")
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "gea.local.json" in content
    assert ".gea" in content


def test_update_gitignore_skips_gea_dir_for_repo_location(tmp_path):
    scaffold.update_gitignore(tmp_path, "repo")
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".gea\n" not in content


def test_update_gitignore_idempotent(tmp_path):
    scaffold.update_gitignore(tmp_path, "home")
    changed_again = scaffold.update_gitignore(tmp_path, "home")
    assert changed_again is False


def test_claude_md_imports_the_shared_orchestrator_instructions(tmp_path):
    scaffold.write_claude_md(tmp_path, "en", "demo", "x")
    scaffold.write_agents_dir(tmp_path, "en", "demo", "en", False, "x")
    assert "@.agents/orchestrator.md" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "gea handoff" in (tmp_path / ".agents" / "orchestrator.md").read_text(encoding="utf-8")
