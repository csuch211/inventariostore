"""Verify all THEME_* constants in app_view.py are properly imported from settings."""

from __future__ import annotations

import ast
from pathlib import Path


def test_theme_constants_imported():
    app_view = Path(__file__).resolve().parents[2] / "src" / "ui" / "app_view.py"
    src = app_view.read_text(encoding="utf-8")
    tree = ast.parse(src)

    used_themes: set[str] = set()
    imported_themes: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id.startswith("THEME_"):
            used_themes.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr.startswith("THEME_"):
            used_themes.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name.startswith("THEME_"):
                    imported_themes.add(alias.asname or alias.name)

    missing = used_themes - imported_themes
    assert not missing, f"THEME_* constants used but not imported: {missing}"
    # Unused imports are a warning, not a failure


def test_no_legacy_alignment_shortcuts():
    """Verify no file uses ft.alignment.<lowercase> (removed in Flet 0.85)."""
    import re

    repo = Path(__file__).resolve().parents[2] / "src"
    pattern = re.compile(r"\bft\.alignment\.[a-z][A-Za-z_]*\b")
    string_lit = re.compile(r""""[^"]*"|'[^']*'""")
    offenders = []

    for src_path in repo.rglob("*.py"):
        if src_path.name == "verify_alignment_api.py":
            continue
        for lineno, line in enumerate(src_path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_only = string_lit.sub("", line)
            if pattern.search(code_only):
                offenders.append((src_path, lineno, stripped))

    assert not offenders, f"Legacy ft.alignment shortcuts found: {offenders}"


def test_alignment_api():
    import flet as ft
    assert hasattr(ft.alignment, "Alignment"), "ft.alignment.Alignment missing"
    assert not hasattr(ft.alignment, "center"), "ft.alignment.center should NOT exist"


def test_all_files_import_cleanly():
    """Verify critical modules import without errors."""
    import importlib
    for module_name in ["config.settings", "utils.exceptions", "utils.logger"]:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            pytest.fail(f"Module {module_name} failed to import: {e}")


import pytest
