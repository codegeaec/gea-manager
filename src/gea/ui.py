"""Minimal terminal UI helpers: colored status lines and simple prompts.

Kept dependency-free (AGENTS.md rule 2) — no `rich`/`click`, just ANSI
codes with a plain fallback when stdout isn't a TTY.
"""

from __future__ import annotations

import sys

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def _supports_color() -> bool:
    return sys.stdout.isatty()


def _wrap(code: str, text: str) -> str:
    return f"{code}{text}{RESET}" if _supports_color() else text


def ok(message: str) -> None:
    print(f"{_wrap(GREEN, '✓')} {message}")


def warn(message: str) -> None:
    print(f"{_wrap(YELLOW, '!')} {message}")


def err(message: str) -> None:
    print(f"{_wrap(RED, '✗')} {message}")


def info(message: str) -> None:
    print(f"{_wrap(BOLD, '==>')} {message}")


def ask_yes_no(question: str, default: bool = True, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes", "s", "si", "sí")


def ask_choice(
    question: str, options: list[str], default_index: int = 0, assume_yes: bool = False
) -> int:
    if assume_yes:
        return default_index
    print(question)
    for i, option in enumerate(options):
        marker = " *" if i == default_index else "  "
        print(f"{marker} {i + 1}) {option}")
    raw = input(f"> [{default_index + 1}] ").strip()
    if not raw:
        return default_index
    try:
        choice = int(raw) - 1
        if 0 <= choice < len(options):
            return choice
    except ValueError:
        pass
    return default_index


def ask_multi(
    question: str, options: list[str], default_all: bool = True, assume_yes: bool = False
) -> list[int]:
    """Pick any number of options: comma-separated numbers, empty = the
    default (all of them, or none). Invalid input falls back to the default."""
    everything = list(range(len(options)))
    default = everything if default_all else []
    if assume_yes:
        return default
    print(question)
    for i, option in enumerate(options):
        print(f"  {i + 1}) {option}")
    raw = input(f"> [{'all' if default_all else 'none'}] ").strip()
    if not raw:
        return default
    try:
        picked = sorted({int(part) - 1 for part in raw.split(",") if part.strip()})
    except ValueError:
        return default
    return picked if all(0 <= i < len(options) for i in picked) else default


def ask_text(question: str, default: str | None = None, assume_yes: bool = False) -> str | None:
    """Free text; empty input gives `default` (None when there is none)."""
    if assume_yes:
        return default
    suffix = f" [{default}]" if default else ""
    return input(f"{question}{suffix} ").strip() or default


def ask_pick(
    question: str,
    options: list[str],
    default: str | None = None,
    assume_yes: bool = False,
    free_text: bool = False,
    page: int = 15,
) -> str | None:
    """Pick one of `options` from a possibly long list: type its number, or type
    text to filter the list. Empty input gives `default`. With `free_text`, text
    that matches nothing is returned as typed (for values the CLI cannot list).
    Returns None if nothing was chosen."""
    if assume_yes:
        return default
    shown = options
    for _ in range(50):  # never spin forever on bad input
        print(question)
        for i, option in enumerate(shown[:page], start=1):
            print(f"  {i}) {option}")
        if len(shown) > page:
            print(f"  … {len(shown) - page} more — type text to filter")
        raw = input(f"> [{default or ''}] ").strip()
        if not raw:
            return default
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < min(len(shown), page):
                return shown[index]
            continue
        matches = [o for o in options if raw.lower() in o.lower()]
        if matches:
            shown = matches
        elif free_text:
            return raw
        else:
            print("  (no match)")
            shown = options
    return None
