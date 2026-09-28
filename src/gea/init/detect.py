"""Stack detection for `gea init`: package manager and verify commands."""

from __future__ import annotations

import json
from pathlib import Path

LOCKFILE_TO_PM = {
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
}

PM_RUNNER = {"pnpm": "pnpm dlx", "npm": "npx", "yarn": "yarn dlx", "bun": "bunx"}

# Common script names to look for in package.json.
LINT_SCRIPTS = ["lint"]
TEST_SCRIPTS = ["test"]


def detect_pm(repo_root: Path) -> str | None:
    for lockfile, pm in LOCKFILE_TO_PM.items():
        if (repo_root / lockfile).exists():
            return pm
    if (repo_root / "package.json").exists():
        return "npm"
    return None


def has_shadcn(repo_root: Path) -> bool:
    return (repo_root / "components.json").exists()


def shadcn_runner(pm: str | None) -> str:
    return PM_RUNNER.get(pm or "npm", "npx")


def _package_json_scripts(repo_root: Path) -> dict[str, str]:
    path = repo_root / "package.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("scripts", {})


def detect_verify_commands(repo_root: Path, pm: str | None) -> list[str]:
    """Best-effort guess of this project's verify commands — always
    confirmed/editable by the user in the wizard, never applied blindly."""
    commands: list[str] = []

    scripts = _package_json_scripts(repo_root)
    if scripts:
        runner = pm or "npm"
        run_prefix = "pnpm" if runner == "pnpm" else f"{runner} run"
        exec_prefix = f"{runner} exec"
        if (repo_root / "tsconfig.json").exists():
            commands.append(f"{exec_prefix} tsc --noEmit")
        for name in LINT_SCRIPTS + TEST_SCRIPTS:
            if name in scripts:
                commands.append(f"{run_prefix} {name}")

    if (repo_root / "pyproject.toml").exists():
        commands.append("uv run ruff check .")
        commands.append("uv run pytest")

    if (repo_root / "Cargo.toml").exists():
        commands.append("cargo check")
        commands.append("cargo test")

    if (repo_root / "go.mod").exists():
        commands.append("go vet ./...")
        commands.append("go test ./...")

    return commands
