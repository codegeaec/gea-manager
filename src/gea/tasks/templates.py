"""Task/subtask markdown templates, in the project's chosen docs language."""

from __future__ import annotations

from pathlib import Path

TASK_TEMPLATE = {
    "en": """# {task_id} - {title}

Status: planned

Created: {date}
Updated: {date}

## Objective

## Context

## Requirements

## Acceptance

- [ ] 

## Existing Implementation

## Plan

### 1. ...

## Files

## Decisions

## Implementation Notes

## Deviations

## Review

## Verification

- [ ] Typecheck
- [ ] Lint
- [ ] Manual verification

## Completion Notes
""",
    "es": """# {task_id} - {title}

Status: planned

Created: {date}
Updated: {date}

## Objective

## Context

## Requirements

## Acceptance

- [ ] 

## Existing Implementation

## Plan

### 1. ...

## Files

## Decisions

## Implementation Notes

## Deviations

## Review

## Verification

- [ ] Tipos
- [ ] Lint
- [ ] Verificación manual

## Completion Notes
""",
}

SUBTASK_TEMPLATE = {
    "en": """# {task_id} - {title}

Parent: {parent_id}
Status: planned
Depends on: {depends}

Created: {date}
Updated: {date}

## Objective

## Requirements

## Existing Implementation

## Plan

## Files

## Decisions

## Implementation Notes

## Deviations

## Review

## Verification

- [ ] Typecheck
- [ ] Lint

## Completion Notes
""",
    "es": """# {task_id} - {title}

Parent: {parent_id}
Status: planned
Depends on: {depends}

Created: {date}
Updated: {date}

## Objective

## Requirements

## Existing Implementation

## Plan

## Files

## Decisions

## Implementation Notes

## Deviations

## Review

## Verification

- [ ] Tipos
- [ ] Lint

## Completion Notes
""",
}


TASK_TYPES = ("bugfix", "feature", "refactor", "spike")
TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"


def _type_template(task_type: str, lang: str) -> str:
    path = TEMPLATES_ROOT / lang / "tasks" / f"{task_type}.md"
    if not path.exists():
        path = TEMPLATES_ROOT / "en" / "tasks" / f"{task_type}.md"
    return path.read_text(encoding="utf-8")


def render_task(
    task_id: str, title: str, date: str, lang: str = "en", task_type: str | None = None
) -> str:
    if task_type:
        if task_type not in TASK_TYPES:
            raise ValueError(f"unknown task type: {task_type} (use {', '.join(TASK_TYPES)})")
        template = _type_template(task_type, lang)
    else:
        template = TASK_TEMPLATE.get(lang, TASK_TEMPLATE["en"])
    return template.format(task_id=task_id, title=title, date=date)


def render_subtask(
    task_id: str, title: str, parent_id: str, depends: str, date: str, lang: str = "en"
) -> str:
    template = SUBTASK_TEMPLATE.get(lang, SUBTASK_TEMPLATE["en"])
    return template.format(
        task_id=task_id, title=title, parent_id=parent_id, depends=depends, date=date
    )
