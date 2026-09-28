"""Exhaustion state: which quota pools are rate-limited and until when.

Stored in `~/gea/state.json`, global — an account's rate limit is the
account's, not a single repo's, so hitting it in one project now correctly
marks it exhausted everywhere.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from gea import paths

EXHAUSTION_PATTERNS = [
    re.compile(r"usage limit reached", re.I),
    re.compile(r"rate limit(ed)?\b", re.I),
    re.compile(r"\b429\b"),
    re.compile(r"quota (exceeded|exhausted)|out of quota|insufficient quota", re.I),
    re.compile(r"quota reached", re.I),
    re.compile(r"retrying in\s+(\d+)\s*m", re.I),
    re.compile(r"resets? at \d", re.I),
]
RETRY_MINUTES_RE = re.compile(
    r"(?:retrying in\s+(\d+)\s*m|resets? in\s+(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?)", re.I
)
DEFAULT_EXHAUST_HOURS = 5


def now() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load() -> dict[str, str]:
    """Map of pool -> exhausted_until (ISO), only entries still in the future."""
    path = paths.global_state_path()
    if not path.exists():
        return {}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    pools = data.get("exhausted", {})
    at = now()
    return {
        pool: until
        for pool, until in pools.items()
        if parse_iso(until) and parse_iso(until) > at
    }


def save(pools: dict[str, str]) -> None:
    path = paths.global_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"exhausted": pools}, indent=2) + "\n", encoding="utf-8")


def is_pool_available(pool: str, pools: dict[str, str] | None = None) -> bool:
    pools = pools if pools is not None else load()
    until = parse_iso(pools.get(pool))
    return until is None or until <= now()


def mark_exhausted(pool: str, until: datetime) -> None:
    pools = load()
    pools[pool] = iso(until)
    save(pools)


def reset_pool(pool: str) -> None:
    pools = load()
    pools.pop(pool, None)
    save(pools)


def detect_exhaustion(text: str) -> datetime | None:
    """Return the exhaustion deadline if `text` looks like a rate-limit
    message, else None."""
    if not any(p.search(text) for p in EXHAUSTION_PATTERNS):
        return None
    match = RETRY_MINUTES_RE.search(text)
    if match:
        retry_minutes, reset_hours, reset_minutes = match.groups()
        minutes = (
            int(retry_minutes)
            if retry_minutes
            else int(reset_hours or 0) * 60 + int(reset_minutes or 0)
        )
    else:
        minutes = DEFAULT_EXHAUST_HOURS * 60
    return now() + timedelta(minutes=minutes)
