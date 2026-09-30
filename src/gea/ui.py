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
