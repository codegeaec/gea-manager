import subprocess

from gea import secrets

DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,0 +2,3 @@
+ok = 1
+key = "AKIAABCDEFGHIJKLMNOP"
+password = "hunter2hunter2hunter2"  # gea:allow-secret
"""


def test_scan_diff_reports_file_line_and_rule_without_the_secret():
    findings = secrets.scan_diff(DIFF)
    assert [(f.path, f.line, f.rule) for f in findings] == [("app.py", 3, "AWS access key")]


def test_scan_diff_ignores_removed_lines():
    diff = "+++ b/a\n@@ -1 +1,0 @@\n-AKIAABCDEFGHIJKLMNOP\n"
    assert secrets.scan_diff(diff) == []


def test_install_hook_never_clobbers_a_foreign_hook(tmp_path):
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-commit").write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    assert secrets.install_hook(tmp_path) == "skipped"
    assert "mine" in (hooks / "pre-commit").read_text(encoding="utf-8")


def test_install_hook_is_idempotent(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    assert secrets.install_hook(tmp_path) == "installed"
    assert secrets.install_hook(tmp_path) == "present"


def test_run_scan_blocks_a_staged_secret(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "a.txt").write_text('token = "ghp_' + "a" * 36 + '"\n', encoding="utf-8")
    git("add", "a.txt")
    assert secrets.run_scan(tmp_path) == 1


def test_hook_runs_the_secret_scan_and_the_strict_lint(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    secrets.install_hook(tmp_path)
    body = (tmp_path / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "gea scan-secrets" in body and "gea lint --strict" in body
    assert "scan-secrets --help" in body  # old installs skip instead of blocking


def test_outdated_gea_hook_is_upgraded_in_place(tmp_path):
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-commit").write_text(f"#!/bin/sh\n{secrets.HOOK_MARKER}\nexec gea scan-secrets\n")
    assert secrets.install_hook(tmp_path) == "installed"
    assert "lint --strict" in (hooks / "pre-commit").read_text(encoding="utf-8")
