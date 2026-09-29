"""Scope guard: compare what a builder touched with the task's `## Files`.

Allowed entries are the backticked paths under `## Files` (globs allowed;
a bare directory allows everything below it). `docs/` and `.gea/` are
always allowed — builders are told to update docs and the task file.
Advisory only: it warns, never blocks.
"""

from __future__ import annotations

import re
from fnmatch import fnmatch

from gea.tasks.sections import section

ALWAYS_ALLOWED = ("docs/", ".gea/")
BACKTICKED = re.compile(r"`([^`]+)`")
CHECKBOX_PREFIX = re.compile(r"^[-*]\s*(\[[ xX]\])?\s*")


def allowed_patterns(task_text: str) -> list[str]:
    return [m.strip() for m in BACKTICKED.findall(section(task_text, "Files")) if m.strip()]


def _matches(path: str, pattern: str) -> bool:
    pattern = pattern.removeprefix("./")
    if fnmatch(path, pattern):
        return True
    return path == pattern.rstrip("/") or path.startswith(pattern.rstrip("/") + "/")


def out_of_scope(files: list[str], patterns: list[str]) -> list[str]:
    """Files matching none of the patterns. Empty `patterns` means the task
    declared no scope, so nothing is out of scope."""
    if not patterns:
        return []
    return [
        f
        for f in files
        if not f.startswith(ALWAYS_ALLOWED) and not any(_matches(f, p) for p in patterns)
    ]


def missing_for_delegation(task_text: str) -> list[str]:
    """Sections a self-sufficient task must fill in before delegating: the
    builder should not have to explore to find its files or its definition
    of done."""
    missing = []
    if not allowed_patterns(task_text):
        missing.append("## Files (list the paths in backticks)")
    bullets = [
        CHECKBOX_PREFIX.sub("", line.strip())
        for line in section(task_text, "Acceptance").splitlines()
        if line.lstrip().startswith(("-", "*"))
    ]
    if not any(bullets):
        missing.append("## Acceptance (one bullet per criterion)")
    return missing
