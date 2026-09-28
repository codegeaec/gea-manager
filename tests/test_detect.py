import json

from gea.init import detect


def test_detect_pm_from_lockfile(tmp_path):
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    assert detect.detect_pm(tmp_path) == "pnpm"


def test_detect_pm_defaults_to_npm_with_package_json_only(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert detect.detect_pm(tmp_path) == "npm"


def test_detect_pm_none_without_any_marker(tmp_path):
    assert detect.detect_pm(tmp_path) is None


def test_has_shadcn(tmp_path):
    assert detect.has_shadcn(tmp_path) is False
    (tmp_path / "components.json").write_text("{}", encoding="utf-8")
    assert detect.has_shadcn(tmp_path) is True


def test_detect_verify_commands_node_project(tmp_path):
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint .", "test": "vitest"}}), encoding="utf-8"
    )
    commands = detect.detect_verify_commands(tmp_path, "pnpm")
    assert "pnpm exec tsc --noEmit" in commands
    assert "pnpm lint" in commands
    assert "pnpm test" in commands


def test_detect_verify_commands_python_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    commands = detect.detect_verify_commands(tmp_path, None)
    assert "uv run pytest" in commands
    assert "uv run ruff check ." in commands


def test_detect_verify_commands_empty_for_unknown_stack(tmp_path):
    assert detect.detect_verify_commands(tmp_path, None) == []
