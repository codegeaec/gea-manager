"""Markdown helpers shared by the task modules."""

from __future__ import annotations

import re


def section(text: str, heading: str) -> str:
    """Body of the `## <heading>` section (up to the next `## `), or ''."""
    match = re.search(
        rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S
    )
    return match.group(1) if match else ""
