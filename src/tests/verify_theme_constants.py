"""Static + runtime check that every THEME_* constant used in app_view.py
is actually imported from config.settings.

This catches the kind of bug where a constant gets used in code but the
import block falls behind (e.g. THEME_DARK_FOCUS_RING). The fix is just
to add the name to the from-import list.
"""

import ast
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
APP_VIEW = _REPO / "src" / "ui" / "app_view.py"

# Parse the file and collect:
#   1. THEME_* identifiers actually used (read in non-import context).
#   2. THEME_* identifiers in the from-import block.
src = APP_VIEW.read_text(encoding="utf-8")
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
unused = imported_themes - used_themes

print(f"THEME_* constants used in app_view.py: {len(used_themes)}")
print(f"THEME_* constants imported:             {len(imported_themes)}")
if missing:
    print("\nMISSING from imports:")
    for m in sorted(missing):
        print(f"  - {m}")
    raise SystemExit(1)
if unused:
    print("\nImported but unused (cleanup):")
    for u in sorted(unused):
        print(f"  - {u}")
print("\nAll THEME_* constants are imported correctly.")

# Runtime check: the module actually loads and _get_colors returns
# the focus_ring key in both modes (this is what the user hit).
sys.path.insert(0, str(_REPO / "src"))
from typing import ClassVar

import flet as ft

from ui.app_view import AppView


class _StubPage:
    theme_mode = ft.ThemeMode.DARK
    title = ""
    theme = None
    dark_theme = None
    padding = 0
    spacing = 0
    bgcolor = ""
    width = 1280
    height = 800
    controls: ClassVar[list] = []
    overlay: ClassVar[list] = []
    _dialogs: ClassVar[list] = []

    def clean(self):
        self.controls.clear()

    def add(self, *a):
        self.controls.extend(a)

    def update(self, *a, **k):
        pass

    def show_dialog(self, d):
        self._dialogs.append(d)

    def pop_dialog(self):
        if self._dialogs:
            self._dialogs.pop()


app = AppView(_StubPage())
app.page.theme_mode = ft.ThemeMode.DARK
dark = app._get_colors()
assert "focus_ring" in dark
app.page.theme_mode = ft.ThemeMode.LIGHT
light = app._get_colors()
assert "focus_ring" in light
print(f"focus_ring dark  = {dark['focus_ring']}")
print(f"focus_ring light = {light['focus_ring']}")
print("\nOK: every THEME_* constant used is imported and _get_colors works.")
