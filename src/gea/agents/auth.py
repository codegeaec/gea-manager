"""Tell "no session" apart from "no tokens" for each installed agent CLI.

- *No session*: the CLI isn't logged in — fixed by logging in.
- *No tokens*: logged in but the quota pool is exhausted (tracked in
  `state.json`, see agents/state.py) — fixed by waiting.

Each CLI has its own way to report login state (verified by hand):
`claude auth status` (JSON), `codex login status` (exit code),
`opencode auth list` ("N credentials"). agy and kimi expose no such
command: agy is judged by its OAuth token file, kimi is reported unknown.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from gea import paths, platform, proc, ui
from gea.agents import profiles, state
from gea.i18n import t

OK, NO_SESSION, UNKNOWN = "ok", "no_session", "unknown"
CLIS = ("claude", "codex", "opencode", "agy", "kimi")
LOGIN_HINTS = {
    "claude": "claude auth login",
    "codex": "codex login",
    "opencode": "opencode auth login",
    "agy": "agy",
    "kimi": "kimi",
}


def _claude() -> str:
    out, _err, code = proc.run(["claude", "auth", "status"])
    try:
        return OK if json.loads(out).get("loggedIn") else NO_SESSION
    except (json.JSONDecodeError, AttributeError):
        return UNKNOWN if code != 0 else NO_SESSION


def _codex() -> str:
    out, err, code = proc.run(["codex", "login", "status"])
    if code == 0 and "logged in" in (out + err).lower():
        return OK
    return NO_SESSION if code != 127 else UNKNOWN


def _opencode() -> str:
    out, _err, code = proc.run(["opencode", "auth", "list"])
    match = re.search(r"(\d+)\s+credentials?", out)
    if code != 0 or not match:
        return UNKNOWN
    return OK if int(match.group(1)) > 0 else NO_SESSION


def _agy() -> str:
    token = paths.home() / ".gemini" / "jetski-standalone-oauth-token"
    return OK if token.exists() else UNKNOWN


CHECKS = {"claude": _claude, "codex": _codex, "opencode": _opencode, "agy": _agy}


def check(cli: str) -> str:
    return CHECKS.get(cli, lambda: UNKNOWN)()


@dataclass
class AgentAuth:
    cli: str
    session: str
    exhausted_until: str | None


def exhausted_until(cli: str) -> str | None:
    pools = state.load()
    for profile in profiles.load_profiles():
        if profile.cli == cli and profile.pool in pools:
            return pools[profile.pool]
    return None


def collect() -> list[AgentAuth]:
    return [
        AgentAuth(cli, check(cli), exhausted_until(cli))
        for cli in CLIS
        if platform.which(cli)
    ]


def print_report() -> None:
    ui.info(t("auth.title"))
    for entry in collect():
        if entry.session == NO_SESSION:
            ui.warn(t("auth.no_session", cli=entry.cli, hint=LOGIN_HINTS[entry.cli]))
        elif entry.exhausted_until:
            ui.warn(t("auth.no_tokens", cli=entry.cli, until=entry.exhausted_until))
        elif entry.session == OK:
            ui.ok(t("auth.ok", cli=entry.cli))
        else:
            ui.warn(t("auth.unknown", cli=entry.cli))
