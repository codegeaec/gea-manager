from gea.setup import shell_rc

LEGACY_RC = """export PATH="$HOME/bin:$PATH"

# herdr: al invocar "herdr" sin argumentos dentro de un repo git,
# abre workspace con shell + claude + un tab por rol de opencode
herdr() {
  if [ $# -eq 0 ]; then
    herdr-repo
  else
    command herdr "$@"
  fi
}

alias ll="ls -la"
"""


def test_find_legacy_snippet(tmp_path):
    rc = tmp_path / ".bashrc"
    rc.write_text(LEGACY_RC, encoding="utf-8")
    assert shell_rc.find_legacy_snippet(rc) is True


def test_find_legacy_snippet_absent(tmp_path):
    rc = tmp_path / ".bashrc"
    rc.write_text('export PATH="$HOME/bin:$PATH"\n', encoding="utf-8")
    assert shell_rc.find_legacy_snippet(rc) is False


def test_remove_legacy_snippet_strips_function_and_keeps_rest(tmp_path):
    rc = tmp_path / ".bashrc"
    rc.write_text(LEGACY_RC, encoding="utf-8")
    changed = shell_rc.remove_legacy_snippet(rc)
    assert changed is True
    new_content = rc.read_text(encoding="utf-8")
    assert "herdr()" not in new_content
    assert 'export PATH="$HOME/bin:$PATH"' in new_content
    assert 'alias ll="ls -la"' in new_content
    backups = list(tmp_path.glob(".bashrc.bak.*"))
    assert len(backups) == 1


def test_remove_legacy_snippet_noop_when_absent(tmp_path):
    rc = tmp_path / ".bashrc"
    rc.write_text('export PATH="$HOME/bin:$PATH"\n', encoding="utf-8")
    assert shell_rc.remove_legacy_snippet(rc) is False


def test_cleanup_legacy_setup(tmp_path, monkeypatch):
    rc = tmp_path / ".bashrc"
    rc.write_text(LEGACY_RC, encoding="utf-8")
    monkeypatch.setattr(shell_rc.paths, "shell_rc_files", lambda: [rc])
    monkeypatch.setattr(shell_rc, "OLD_HERDR_REPO", tmp_path / "herdr-repo")
    actions = shell_rc.cleanup_legacy_setup()
    assert len(actions) == 1
    assert "herdr()" not in rc.read_text(encoding="utf-8")
