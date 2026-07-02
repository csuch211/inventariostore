"""
Tests for the new sidebar components in ui/components.py.

The previous sidebar had a single flat list of 24 items with no grouping,
every item filled with a solid brand color. The new design follows Linear /
Notion / Stripe Dashboard patterns:

  - Items grouped into collapsible sections.
  - Active item gets a primary_tint background + accent strip + bold text
    (no more full-row solid color).
  - Inactive items are transparent; hover lifts them to hover_tint.
  - Search input filters items across sections.
  - User card footer replaces the plain-text "Usuario/Rol/Permisos" block.

Run:
    cd src && .venv/Scripts/python.exe tests/test_sidebar_components.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

import flet as ft

from ui.components import (
    SidebarItem,
    SidebarSearch,
    SidebarSection,
    SidebarUserCard,
)

PASS = "✔"
FAIL = "✘"
results: list[tuple] = []


def record(name: str, ok: bool, msg: str = "") -> None:
    results.append((name, ok, msg))
    icon = PASS if ok else FAIL
    line = f"  {icon} {name}"
    if msg:
        line += f" - {msg}"
    print(line)


def section(title: str) -> None:
    print(f"\n-- {title} --")


C = {
    "primary": "#2563EB",
    "primary_tint": "#EFF6FF",
    "hover_tint": "#DBEAFE",
    "accent": "#DC2626",
    "surface": "#FFFFFF",
    "divider": "#CBD5E1",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _walk(control: ft.Control):
    """Yield control and every descendant reachable via .controls / .content /
    .leading / .title / .trailing / .border / .shadow / .padding etc."""
    yield control
    for attr in ("controls",):
        children = getattr(control, attr, None)
        if children:
            for c in children:
                yield from _walk(c)
    content = getattr(control, "content", None)
    if content is not None and content is not control:
        yield from _walk(content)
    for attr in ("leading", "title", "trailing", "prefix_icon", "icon"):
        sub = getattr(control, attr, None)
        if sub is not None and isinstance(sub, ft.Control):
            yield from _walk(sub)


def _has_text(control: ft.Control, needle: str) -> bool:
    return any(isinstance(c, ft.Text) and needle in (c.value or "") for c in _walk(control))


def _has_icon(control: ft.Control, expected) -> bool:
    return any(isinstance(c, ft.Icon) and c.name == expected for c in _walk(control))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sidebar_item_active_uses_primary_tint_not_brand_color() -> None:
    si = SidebarItem(
        route="dashboard",
        icon=ft.icons.Icons.DASHBOARD,
        label="Inicio",
        colors=C,
        is_active=True,
    )
    record(
        "Active item uses primary_tint background (not full brand color)",
        si.control.bgcolor == C["primary_tint"],
        f"bgcolor={si.control.bgcolor}",
    )


def test_sidebar_item_inactive_is_transparent() -> None:
    si = SidebarItem(
        route="products",
        icon=ft.icons.Icons.INVENTORY_2_OUTLINED,
        label="Productos",
        colors=C,
        is_active=False,
    )
    record(
        "Inactive item is transparent (no per-row solid fill)",
        si.control.bgcolor == "transparent",
        f"bgcolor={si.control.bgcolor}",
    )


def test_sidebar_item_outlined_icon_when_inactive_filled_when_active() -> None:
    """The caller passes a lowercase form (typical in this codebase) so the
    component must add the _OUTLINED suffix for inactive and strip it for
    active. We check via str() so the test works whether _resolve_outlined
    returns an enum member or a plain string."""
    inactive = SidebarItem(
        route="x",
        icon="inventory_2",
        label="X",
        colors=C,
    )
    active = SidebarItem(
        route="x",
        icon="inventory_2",
        label="X",
        colors=C,
        is_active=True,
    )

    def _icon_names(control):
        names = []
        for c in _walk(control):
            if isinstance(c, ft.Icon):
                v = c.icon
                if hasattr(v, "name"):
                    names.append(v.name)
                else:
                    names.append(str(v))
        return names

    inactive_names = _icon_names(inactive.control)
    active_names = _icon_names(active.control)
    record(
        "Inactive uses the OUTLINED variant",
        any("OUTLINED" in n.upper() and "INVENTORY" in n.upper() for n in inactive_names),
        f"icons={inactive_names}",
    )
    record(
        "Active uses the FILLED variant (no OUTLINED suffix)",
        not any("OUTLINED" in n.upper() for n in active_names)
        and any("INVENTORY" in n.upper() for n in active_names),
        f"icons={active_names}",
    )


def test_sidebar_item_badge_renders_when_present() -> None:
    si = SidebarItem(
        route="stock_alerts",
        icon=ft.icons.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,
        label="Alertas",
        colors=C,
        badge=42,
    )
    record(
        "Badge shows the count (or 99+) when present",
        _has_text(si.control, "42"),
        f"texts={[c.value for c in _walk(si.control) if isinstance(c, ft.Text)]}",
    )


def test_sidebar_item_badge_caps_at_99_plus() -> None:
    si = SidebarItem(
        route="x",
        icon=ft.icons.Icons.WARNING_AMBER,
        label="X",
        colors=C,
        badge=12345,
    )
    record(
        "Badge over 99 displays as '99+' to keep the pill compact",
        _has_text(si.control, "99+"),
        "see walked texts",
    )


def test_sidebar_item_active_has_accent_strip() -> None:
    si = SidebarItem(
        route="dashboard",
        icon=ft.icons.Icons.DASHBOARD,
        label="Inicio",
        colors=C,
        is_active=True,
    )
    # The accent strip is a 3x20 Container with bgcolor=primary.
    strips = [
        c
        for c in _walk(si.control)
        if isinstance(c, ft.Container)
        and getattr(c, "width", None) == 3
        and getattr(c, "height", None) == 20
    ]
    record(
        "Active item shows a left accent strip",
        len(strips) == 1 and strips[0].bgcolor == C["primary"],
        f"strips={len(strips)}",
    )


def test_sidebar_section_collapse_toggle() -> None:
    a = SidebarItem("x", ft.icons.Icons.DASHBOARD, "A", C)
    b = SidebarItem("y", ft.icons.Icons.PERSON, "B", C)
    sec = SidebarSection(title="Test", items=[a, b], colors=C)
    record("SidebarSection default expanded", not sec.collapsed, "")
    sec.set_collapsed(True)
    record(
        "SidebarSection collapses on toggle",
        sec.collapsed is True,
        f"collapsed={sec.collapsed}",
    )
    # When collapsed, the items are not rendered in the body.
    body_items = [
        c
        for c in _walk(sec.control)
        if isinstance(c, ft.Container) and getattr(c, "height", None) == 0
    ]
    record(
        "Collapsed section body is a zero-height container (items hidden)",
        len(body_items) >= 1,
        f"zero-height containers={len(body_items)}",
    )
    sec.set_collapsed(False)
    record("Section re-expands", sec.collapsed is False, "")


def test_sidebar_section_on_toggle_callback() -> None:
    captured: list[bool] = []
    a = SidebarItem("x", ft.icons.Icons.DASHBOARD, "A", C)
    sec = SidebarSection(
        title="Test",
        items=[a],
        colors=C,
        on_toggle=captured.append,
    )
    # The toggle callback fires from the click on the section header, not
    # from programmatic set_collapsed (which is for restoring persisted
    # state without re-notifying).
    header = sec.control.controls[0]  # first child is the header container
    header.on_click(None)
    header.on_click(None)
    record(
        "Collapse toggle notifies caller (for persistence)",
        captured == [True, False],
        f"events={captured}",
    )


def test_sidebar_search_filters_by_label() -> None:
    captured: list[str] = []
    a = SidebarItem("dashboard", ft.icons.Icons.DASHBOARD, "Inicio", C)
    b = SidebarItem("products", ft.icons.Icons.INVENTORY_2_OUTLINED, "Productos", C)

    def _on_filter(q):
        captured.append(q)
        # Mimic the wiring in app_view.py.
        for it in (a, b):
            it.control.visible = (not q) or (q in it.label.lower())

    s = SidebarSearch(colors=C, on_filter=_on_filter)
    s._field.value = "ini"
    s._field.on_change(SimpleNamespace(control=s._field))
    record(
        "Search callback receives the query",
        captured == ["ini"],
        f"queries={captured}",
    )
    record(
        "Items whose label matches are made visible",
        a.control.visible is True,
        f"a.visible={a.control.visible}",
    )


def test_sidebar_user_card_has_avatar_role_and_actions() -> None:
    clicked: list[str] = []
    card = SidebarUserCard(
        username="alice",
        role="admin",
        colors=C,
        on_settings=lambda: clicked.append("settings"),
        on_logout=lambda: clicked.append("logout"),
    )
    record(
        "User card shows the username",
        _has_text(card.control, "alice"),
        "",
    )
    record(
        "User card shows the role",
        _has_text(card.control, "admin"),
        "",
    )
    record(
        "User card shows the avatar initial",
        _has_text(card.control, "A"),
        "",
    )
    # Trigger the two action buttons.
    icon_buttons = [c for c in _walk(card.control) if isinstance(c, ft.IconButton)]
    record(
        "User card has 2 IconButtons (settings + logout)",
        len(icon_buttons) == 2,
        f"iconbuttons={len(icon_buttons)}",
    )
    # Fire the on_click handlers via simulating an event.
    for ib in icon_buttons:
        ib.on_click(SimpleNamespace(control=ib))
    record(
        "Settings + logout callbacks fire",
        set(clicked) == {"settings", "logout"},
        f"events={clicked}",
    )


def test_user_card_avatar_color_is_stable() -> None:
    card1 = SidebarUserCard(username="alice", role="admin", colors=C)
    card2 = SidebarUserCard(username="alice", role="admin", colors=C)

    # The first Container of width=32 height=32 is the avatar.
    def _avatar_bg(card):
        for c in _walk(card.control):
            if isinstance(c, ft.Container) and getattr(c, "width", None) == 32:
                return c.bgcolor
        return None

    record(
        "Same username → same avatar color (deterministic)",
        _avatar_bg(card1) == _avatar_bg(card2),
        f"bgs={_avatar_bg(card1)}, {_avatar_bg(card2)}",
    )
    card3 = SidebarUserCard(username="zoe", role="admin", colors=C)
    record(
        "Different usernames can have different avatar colors",
        _avatar_bg(card1) != _avatar_bg(card3) or _avatar_bg(card1) is None,
        f"alice={_avatar_bg(card1)} zoe={_avatar_bg(card3)}",
    )


def test_old_sidebar_no_solid_color_per_item() -> None:
    """Regression guard: the old sidebar painted every row with the brand
    primary color. The new design must NOT do that for inactive rows."""
    inactive = SidebarItem(
        route="products",
        icon=ft.icons.Icons.INVENTORY_2_OUTLINED,
        label="Productos",
        colors=C,
    )
    record(
        "Old behaviour is gone: inactive row is not the brand primary",
        inactive.control.bgcolor != C["primary"],
        f"bgcolor={inactive.control.bgcolor}",
    )


def run() -> None:
    section("SidebarItem — visual states")
    try:
        test_sidebar_item_active_uses_primary_tint_not_brand_color()
        test_sidebar_item_inactive_is_transparent()
        test_sidebar_item_outlined_icon_when_inactive_filled_when_active()
        test_sidebar_item_active_has_accent_strip()
        test_old_sidebar_no_solid_color_per_item()
    except Exception:
        record("SidebarItem visual states", False, traceback.format_exc())

    section("SidebarItem — badge")
    try:
        test_sidebar_item_badge_renders_when_present()
        test_sidebar_item_badge_caps_at_99_plus()
    except Exception:
        record("SidebarItem badge", False, traceback.format_exc())

    section("SidebarSection")
    try:
        test_sidebar_section_collapse_toggle()
        test_sidebar_section_on_toggle_callback()
    except Exception:
        record("SidebarSection", False, traceback.format_exc())

    section("SidebarSearch")
    try:
        test_sidebar_search_filters_by_label()
    except Exception:
        record("SidebarSearch", False, traceback.format_exc())

    section("SidebarUserCard")
    try:
        test_sidebar_user_card_has_avatar_role_and_actions()
        test_user_card_avatar_color_is_stable()
    except Exception:
        record("SidebarUserCard", False, traceback.format_exc())


def main() -> None:
    run()
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"\n=== Resultado: {passed}/{len(results)} OK, {failed} FAIL ===")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
