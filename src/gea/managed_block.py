"""A block of text a file shares with the user, delimited by markers so it
can be regenerated (or removed) without touching anything else in the file.

Used for the global agent instructions (`~/.claude/CLAUDE.md`, ...) and for
a project's existing AGENTS.md / CLAUDE.md / README.md.
"""

from __future__ import annotations

from pathlib import Path

from gea import dryrun

START_MARKER = "<!-- gea:start -->"
END_MARKER = "<!-- gea:end -->"


def render(body: str) -> str:
    return f"{START_MARKER}\n{body.strip()}\n{END_MARKER}\n"


def has_block(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return START_MARKER in text and END_MARKER in text


def upsert(path: Path, body: str) -> bool:
    """Insert or replace the block in `path`, creating the file (and parent
    dirs) if needed. Content outside the markers is never touched. Returns
    True if the file changed."""
    block = render(body)
    if not path.exists():
        original, new_content = None, block
    else:
        original = path.read_text(encoding="utf-8")
        if START_MARKER in original and END_MARKER in original:
            before, rest = original.split(START_MARKER, 1)
            _old, after = rest.split(END_MARKER, 1)
            new_content = before + block.rstrip("\n") + after
        else:
            separator = "\n\n" if original and not original.endswith("\n\n") else ""
            new_content = original + separator + block
    if new_content == original:
        return False
    if dryrun.active():
        dryrun.report(f"update the gea block in {path}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_content, encoding="utf-8")
    return True


def remove(path: Path) -> bool:
    """Strip the block from `path`. Returns True if the file changed."""
    if not has_block(path):
        return False
    original = path.read_text(encoding="utf-8")
    before, rest = original.split(START_MARKER, 1)
    _block, after = rest.split(END_MARKER, 1)
    remaining = (before.rstrip("\n") + "\n" + after.lstrip("\n")).strip("\n")
    if dryrun.active():
        dryrun.report(f"remove the gea block from {path}")
        return True
    path.write_text(remaining + "\n" if remaining else "", encoding="utf-8")
    return True
