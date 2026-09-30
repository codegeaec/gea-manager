"""The short "what exists / what gea will do" report shown before `gea init`
asks anything. Pure presentation over `inspect.ProjectState`."""

from __future__ import annotations

from gea import ui
from gea.i18n import t
from gea.init.inspect import ProjectState


def print_report(state: ProjectState) -> None:
    ui.info(t("init.report_existing") if state.is_existing else t("init.report_new"))
    if state.has_agents_md:
        ui.ok(t("init.report_agents_md", tokens=state.agents_md_tokens))
    if state.has_claude_md:
        ui.ok(t("init.report_claude_md"))
    if state.agents_files:
        ui.ok(t("init.report_agents_dir", count=len(state.agents_files)))
    for generated, existing in state.equivalents.items():
        ui.ok(t("init.report_equivalent", generated=generated, existing=existing))
    for layout in state.task_layouts:
        ui.ok(t("init.report_tasks", layout=str(layout)))
    if state.agents_md_oversized:
        ui.warn(t("init.warn_oversized", tokens=state.agents_md_tokens))
    for location in state.shadcn_mcp:
        ui.warn(t("init.warn_shadcn_mcp", location=location))
