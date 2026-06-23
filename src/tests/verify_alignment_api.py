"""Regression test for the ft.alignment API change.

In Flet 0.85, ``ft.alignment`` is a module that exposes the ``Alignment``
enum, but the convenient ``ft.alignment.center`` shortcut that existed in
older releases is gone. This test guards against silently regressing to
the old shortcut and breaking runtime at import time.
"""

import re
import sys
from pathlib import Path

import flet as ft

_REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))

import ui.app_view  # noqa: E402
import ui.charts  # noqa: E402, F401

# These imports will raise AttributeError on app_view / charts if
# any module still uses ft.alignment.center (the missing shortcut).

# Sanity: confirm the new API works and the old shortcut really is gone.
assert hasattr(ft.alignment, "Alignment"), "ft.alignment.Alignment missing"
assert not hasattr(ft.alignment, "center"), (
    "ft.alignment.center should NOT exist in Flet 0.85; if it does, the "
    "codebase may need to track both shapes."
)

# Confirm the affected modules import cleanly. ``views.py`` (legacy
# InventarioView) was removed during the dashboard dedup; the modern
# dashboard lives in ui.app_view.
# Static guard: scan every Python source file under src/ for the legacy
# ``ft.alignment.<shortcut>`` pattern (e.g. ``ft.alignment.center``).
# Flet 0.85 dropped those shortcuts in favor of ``ft.alignment.Alignment.CENTER``;
# using the old form crashes the app at first render (e.g. on login).
# This catches regressions before they ship.
_LEGACY_ALIGNMENT = re.compile(r"\bft\.alignment\.[a-z][A-Za-z_]*\b")
_offenders: list[tuple[str, int, str]] = []
for src_path in (_REPO / "src").rglob("*.py"):
    # This file intentionally documents the legacy pattern; don't scan it.
    if src_path.name == "verify_alignment_api.py":
        continue
    in_docstring = False
    for lineno, line in enumerate(src_path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        # Skip pure comment lines.
        if stripped.startswith("#"):
            continue
        # Track triple-quoted docstring boundaries so we skip them too.
        triple_count = line.count('"""')
        if triple_count % 2 == 1:
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if _LEGACY_ALIGNMENT.search(line):
            # Allow the bare ``ft.alignment.Alignment.*`` enum form.
            if ".Alignment." in line:
                continue
            _offenders.append((str(src_path.relative_to(_REPO)), lineno, line.strip()))
assert not _offenders, (
    "Found legacy ft.alignment.<shortcut> usage; use "
    "ft.alignment.Alignment.<ENUM> instead:\n"
    + "\n".join(f"  {p}:{n}: {line}" for p, n, line in _offenders)
)

# Also confirm that constructing the empty-state container from
# _show_stock_alerts doesn't blow up — that's where the user hit the bug.
C = {
    "text_muted": "#888",
    "surface": "#fff",
}
container = ft.Container(
    content=ft.Column(
        [ft.Icon(ft.icons.Icons.SEARCH_OFF, size=48, color="#888")],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    ),
    padding=60,
    alignment=ft.alignment.Alignment.CENTER,
    expand=True,
)
assert container is not None

print("OK: ft.alignment API migrated to Alignment enum, no regressions")
