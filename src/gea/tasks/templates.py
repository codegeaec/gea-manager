"""Task/subtask markdown templates, in the project's chosen docs language."""

from __future__ import annotations

TASK_TEMPLATE = {
    "en": """# {task_id} - {title}

Status: planned

Created: {date}
Updated: {date}

## Objective

## Context

## Requirements

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


def render_task(task_id: str, title: str, date: str, lang: str = "en") -> str:
    template = TASK_TEMPLATE.get(lang, TASK_TEMPLATE["en"])
    return template.format(task_id=task_id, title=title, date=date)


def render_subtask(
    task_id: str, title: str, parent_id: str, depends: str, date: str, lang: str = "en"
) -> str:
    template = SUBTASK_TEMPLATE.get(lang, SUBTASK_TEMPLATE["en"])
    return template.format(
        task_id=task_id, title=title, parent_id=parent_id, depends=depends, date=date
    )
