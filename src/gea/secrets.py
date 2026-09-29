"""`gea scan-secrets` — regex scan of the lines a commit *adds*.

Meant to run as a git pre-commit hook (installed by `gea init`). Findings
report file, line and rule — never the matched text. Append
`gea:allow-secret` to a line to whitelist a known false positive.
"""

from __future__ import annotations

import re
import stat
from dataclasses import dataclass
from pathlib import Path

from gea import dryrun, proc, ui
from gea.i18n import t

ALLOW_MARKER = "gea:allow-secret"
HOOK_MARKER = "# gea:secret-scan"
HOOK_BODY = f"""#!/bin/sh
{HOOK_MARKER}
command -v gea >/dev/null 2>&1 || exit 0
gea scan-secrets && gea lint --strict
"""

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    (
        "hardcoded credential",
        re.compile(
            r"""(?i)\b(?:password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*["'][^"'\s]{12,}["']"""
        ),
    ),
]

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


@dataclass
class Finding:
    path: str
    line: int
    rule: str


def scan_diff(diff: str) -> list[Finding]:
    """Scan a `git diff -U0` text, looking only at added lines."""
    findings: list[Finding] = []
    path = ""
    line_no = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].removeprefix("b/")
            continue
        hunk = HUNK_RE.match(raw)
        if hunk:
            line_no = int(hunk.group(1))
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:]
            if ALLOW_MARKER not in text:
                for rule, pattern in RULES:
                    if pattern.search(text):
                        findings.append(Finding(path, line_no, rule))
                        break
            line_no += 1
    return findings


def run_scan(repo_root: Path | None = None) -> int:
    root = str(repo_root or Path.cwd())
    out, err, code = proc.run(["git", "-C", root, "diff", "--cached", "-U0", "--no-color"])
    if code != 0:
        ui.err(t("secrets.git_failed", error=err.strip()))
        return 1
    findings = scan_diff(out)
    for f in findings:
        ui.err(t("secrets.finding", path=f.path, line=f.line, rule=f.rule))
    if findings:
        ui.warn(t("secrets.blocked", marker=ALLOW_MARKER))
        return 1
    return 0


def install_hook(repo_root: Path) -> str:
    """Install the pre-commit hook. Returns 'installed', 'present' or
    'skipped' (a foreign pre-commit hook already exists — never clobbered)."""
    hook = repo_root / ".git" / "hooks" / "pre-commit"
    if not hook.parent.is_dir():
        return "skipped"
    if hook.exists():
        current = hook.read_text(encoding="utf-8")
        if HOOK_MARKER not in current:
            return "skipped"
        if current == HOOK_BODY:
            return "present"
    if dryrun.active():
        dryrun.report(f"install the secret-scan hook at {hook}")
        return "installed"
    hook.write_text(HOOK_BODY, encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return "installed"
