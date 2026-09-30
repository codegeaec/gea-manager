"""Read-only look at a repo before `gea init` touches it: what already
exists (so init adds around it instead of over it), what would collide, and
what deserves a warning. Nothing here writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gea import shadcn
from gea.lint_context import MAX_INSTRUCTION_TOKENS, estimate_tokens

# What gea would generate under `.agents/` -> filename keyword that means
# "the project already has its own equivalent" (e.g. convenciones-commits.md).
EQUIVALENT_KEYWORDS = {
    "commit-conventions.md": ("commit",),
    "gotchas.md": ("gotcha",),
}


@dataclass
class ProjectState:
    has_agents_md: bool = False
    has_claude_md: bool = False
    has_readme: bool = False
    has_docs: bool = False
    agents_md_tokens: int = 0
    claude_md_tokens: int = 0
    agents_files: list[str] = field(default_factory=list)
    equivalents: dict[str, str] = field(default_factory=dict)
    shadcn_mcp: list[str] = field(default_factory=list)
    task_layouts: list = field(default_factory=list)

    @property
    def is_existing(self) -> bool:
        return bool(
            self.has_agents_md or self.has_claude_md or self.agents_files or self.task_layouts
        )

    @property
    def agents_md_oversized(self) -> bool:
        return self.agents_md_tokens > MAX_INSTRUCTION_TOKENS


def _tokens(path: Path) -> int:
    return estimate_tokens(path.read_text(encoding="utf-8", errors="replace"))


def find_equivalent(agents_dir: Path, generated_name: str) -> str | None:
    """A file already in `.agents/` that plays the role of `generated_name`."""
    keywords = EQUIVALENT_KEYWORDS.get(generated_name, ())
    if not agents_dir.is_dir():
        return None
    for path in sorted(agents_dir.glob("*.md")):
        if path.name != generated_name and any(k in path.name.lower() for k in keywords):
            return path.name
    return None


def inspect(repo_root: Path) -> ProjectState:
    state = ProjectState()
    agents_md, claude_md = repo_root / "AGENTS.md", repo_root / "CLAUDE.md"
    state.has_agents_md, state.has_claude_md = agents_md.is_file(), claude_md.is_file()
    state.agents_md_tokens = _tokens(agents_md) if state.has_agents_md else 0
    state.claude_md_tokens = _tokens(claude_md) if state.has_claude_md else 0
    state.has_readme = (repo_root / "README.md").is_file()
    state.has_docs = (repo_root / "docs").is_dir()

    agents_dir = repo_root / ".agents"
    if agents_dir.is_dir():
        state.agents_files = sorted(p.name for p in agents_dir.glob("*.md"))
    for name in EQUIVALENT_KEYWORDS:
        found = find_equivalent(agents_dir, name)
        if found:
            state.equivalents[name] = found

    state.shadcn_mcp = [
        hit.location for hit in shadcn.detect_mcp_servers(repo_root) if "project" in hit.location
    ]
    return state
