"""`gea doctor` — read-only check of the tools gea depends on.

Never installs anything (that's `gea setup`'s job) — safe to run anytime.
"""

from __future__ import annotations

from dataclasses import dataclass

from gea import platform, shadcn
from gea.i18n import t

# (binary name, i18n key) — the base toolchain gea itself needs.
REQUIRED_TOOLS: list[tuple[str, str]] = [
    ("git", "doctor.tool_git"),
    ("gh", "doctor.tool_gh"),
    ("jq", "doctor.tool_jq"),
    ("uv", "doctor.tool_uv"),
    ("herdr", "doctor.tool_herdr"),
]

# Present but optional — missing these only lowers capability, not a hard
# failure (rtk/codegraph give token savings; absence is just a warning).
OPTIONAL_TOOLS: list[tuple[str, str]] = [
    ("rtk", "doctor.tool_rtk"),
    ("codegraph", "doctor.tool_codegraph"),
]


@dataclass
class DoctorResult:
    missing_required: list[str]
    missing_optional: list[str]
    shadcn_mcp_found: list[str]

    @property
    def is_healthy(self) -> bool:
        return not self.missing_required and not self.missing_optional and not self.shadcn_mcp_found


def run_doctor() -> DoctorResult:
    missing_required = [name for name, _key in REQUIRED_TOOLS if not platform.which(name)]
    missing_optional = [name for name, _key in OPTIONAL_TOOLS if not platform.which(name)]
    shadcn_hits = shadcn.detect_mcp_servers()
    return DoctorResult(
        missing_required=missing_required,
        missing_optional=missing_optional,
        shadcn_mcp_found=[hit.location for hit in shadcn_hits],
    )


def print_report(result: DoctorResult) -> None:
    from gea import ui

    ui.info(t("doctor.title"))
    for name, key in REQUIRED_TOOLS + OPTIONAL_TOOLS:
        label = t(key)
        if name in result.missing_required or name in result.missing_optional:
            ui.warn(f"{label}: {t('doctor.missing')}")
        else:
            ui.ok(f"{label}: {t('doctor.ok')}")
    for location in result.shadcn_mcp_found:
        ui.warn(f"{t('doctor.tool_shadcn_mcp')}: {location}")

    total_missing = len(result.missing_required) + len(result.missing_optional)
    if result.is_healthy:
        ui.ok(t("doctor.summary_ok"))
    else:
        ui.warn(t("doctor.summary_missing", count=total_missing))
